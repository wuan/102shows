"""
Driver for APA102 LED strips (aka "DotStar")

(c) 2015 Martin Erzberger, 2016 Simon Leiner

Very brief overview of APA102: An APA102 LED is addressed with SPI. The bits are shifted in one by one,
starting with the least significant bit.

An LED usually just forwards everything that is sent to its data-in to data-out. While doing this, it
remembers its own color and keeps glowing with that color as long as there is power.

An LED can be switched to not forward the data, but instead use the data to change it's own color.
This is done by sending (at least) 32 bits of zeroes to data-in. The LED then accepts the next
correct 32 bit LED frame (with color information) as its new color setting.

After having received the 32 bit color frame, the LED changes color, and then resumes to just copying
data-in to data-out.

The really clever bit is this: While receiving the 32 bit LED frame, the LED sends zeroes on its
data-out line. Because a color frame is 32 bits, the LED sends 32 bits of zeroes to the next LED.
As we have seen above, this means that the next LED is now ready to accept a color frame and
update its color.

So that's really the entire protocol:
- Start by sending 32 bits of zeroes. This prepares LED 1 to update its color.
- Send color information one by one, starting with the color for LED 1, then LED 2 etc.
- Finish off by cycling the clock line a few times to get all data to the very last LED on the strip

The last step is necessary, because each LED delays forwarding the data a bit. Imagine ten people in
a row. When you yell the last color information, i.e. the one for person ten, to the first person in
the line, then you are not finished yet. Person one has to turn around and yell it to person 2, and
so on. So it takes ten additional "dummy" cycles until person ten knows the color. When you look closer,
you will see that not even person 9 knows the color yet. This information is still with person 2.
Essentially the driver sends additional zeroes to LED 1 as long as it takes for the last color frame
to make it down the line to the last LED.

Restrictions:
    - strips cannot have more than 1024 LEDs

"""

import spidev

from drivers.abstract import LEDStrip


class APA102(LEDStrip):
    def initialize_strip_connection(self):
        """ initializes the strip connection via SPI """
        # check if we do not have too much LEDs in the strip
        if self.num_leds > 1024:
            raise Exception("The APA102 LED driver does not support strips of more than 1024 LEDs")

        # SPI connection
        self.spi = spidev.SpiDev()  # Init the SPI device
        self.spi.open(0, 1)  # Open SPI port 0, slave device (CS)  1
        self.spi.max_speed_hz = self.max_clock_speed_hz  # should not be higher than 8000000

    def clock_start_frame(self):
        """ This method clocks out a start frame, telling the receiving LED that it must update its own color now. """
        self.spi.xfer2([0] * 4)  # Start frame, 4 empty bytes <=> 32 zero bits

    @classmethod
    def assemble_spi_message(cls, color_buffer: list, brightness_buffer: list) -> list:
        """
        assembles a message that contains the state for the whole strip to be sent out via SPI

        :param color_buffer: a list of (r,g,b) color tuples
        :param brightness_buffer: a list of integers between 0 and 100. Must have the same dimension as color_buffer!
        :return:
        """
        num_leds = len(color_buffer)
        spi_msg = []

        for led_num in range(num_leds):
            # for each led the spi message consists of 4 bytes:
            #   1. Prefix: as generated by led_prefix(brightness)
            #   2. Blue grayscale:  8 bits <=> 256 steps
            #   3. Green grayscale: 8 bits <=> 256 steps
            #   4. Red grayscale:   8 bits <=> 256 steps
            prefix = cls.led_prefix(brightness_buffer[led_num])
            red, green, blue = color_buffer[led_num]

            spi_msg.append(prefix)
            spi_msg.append(blue)
            spi_msg.append(green)
            spi_msg.append(red)

        return spi_msg

    @classmethod
    def led_prefix(cls, brightness: int) -> int:
        """
        generates the first byte of a 4-byte SPI message to a single APA102 module

        :param brightness: integer from 0 (off) to 100 (full brightness)
        :return: the brightness byte
        """

        # map 0 - 100 brightness parameter to 0 - 31 integer as used in the APA102 prefix byte
        brightness_byte = round(brightness / 100 * 31)

        # structure of the prefix byte: (1 1 1 b4 b3 b2 b1 b0)
        #    - the first three ones are fixed
        #    - (b4, b3, b2, b1, b0) is the binary brightness value (5 bit <=> 32 steps - from 0 to 31)
        prefix_byte = (brightness_byte & 0b00011111) | 0b11100000

        return prefix_byte

    def show(self):
        """ sends the buffered color and brightness values to the strip """
        self.clock_start_frame()

        spi_buffer = self.assemble_spi_message(self.color_buffer, self.brightness_buffer)
        self.spi.xfer2(spi_buffer)  # SPI takes up to 4096 Integers. So we are fine for up to 1024 LEDs.

        self.clock_end_frame()

    def clock_end_frame(self):
        """
        As explained above, dummy data must be sent after the last real color information so that all of the data
        can reach its destination down the line.
        The delay is not as bad as with the human example above. It is only 1/2 bit per LED. This is because the
        SPI clock line needs to be inverted.

        Say a bit is ready on the SPI data line. The sender communicates this by toggling the clock line. The bit
        is read by the LED, and immediately forwarded to the output data line. When the clock goes down again
        on the input side, the LED will toggle the clock up on the output to tell the next LED that the bit is ready.

        After one LED the clock is inverted, and after two LEDs it is in sync again, but one cycle behind. Therefore,
        for every two LEDs, one bit of delay gets accumulated. For 300 LEDs, 150 additional bits must be fed to
        the input of LED one so that the data can reach the last LED.

        Ultimately, we need to send additional num_leds/2 arbitrary data bits, in order to trigger num_leds/2
        additional clock changes. This driver sends zeroes, which has the benefit of getting LED one partially or
        fully ready for the next update to the strip. An optimized version of the driver could omit the
        "clock_start_frame" method if enough zeroes have been sent as part of "clock_end_frame".
        """
        for _ in range((self.num_leds + 15) // 16):  # Round up num_leds/2 bits (or num_leds/16 bytes)
            self.spi.xfer2([0x00])
