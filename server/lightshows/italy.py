#!/usr/bin/env python3

import logging

from drivers import LEDStrip
from helpers import verify
from helpers.color import SmoothBlend
from helpers.exceptions import InvalidStrip
from lightshows.templates.base import Lightshow

log = logging.getLogger(__name__)


class Italy(Lightshow):
    """\
    Rotates a rainbow color wheel around the strip.

    No parameters necessary
    """

    def __init__(self, strip: LEDStrip, parameters: dict):
        super().__init__(strip, parameters)
        self.state = {}
        self.stripe = 1
        self.balls = ()
        self.spare_colors = [(0, 255, 255)]

    def init_parameters(self):
        pass

    def run(self):
        transition = SmoothBlend(self.strip)
        red_pixels = self.layout.block // 3
        green_pixels = 2 * self.layout.block // 3
        for index in range(red_pixels):
            self.layout.set_pixel_func(transition.set_pixel, index, 255, 0.0, 0.0)
        for index in range(red_pixels, green_pixels):
            self.layout.set_pixel_func(transition.set_pixel, index, 255, 255, 255)
        for index in range(green_pixels, self.layout.block):
            self.layout.set_pixel_func(transition.set_pixel, index, 0, 255, 0)
        transition.blend()

    def check_runnable(self):
        # do we have at least one LED?
        if self.strip.num_leds < 1:
            raise InvalidStrip("This show needs a strip of at least {} LEDs to run!".format(self.strip.num_leds))
