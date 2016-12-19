"""
102shows Configuration File Parser
(c) 2016 Simon Leiner
"""

import yaml
from copy import deepcopy
from orderedattrdict.yamlutils import from_yaml
from orderedattrdict import AttrDict as ConfigTree

# Load YAML always as AttrDict (aka ConfigTree)
yaml.add_constructor(u'tag:yaml.org,2002:map', from_yaml)
yaml.add_constructor(u'tag:yaml.org,2002:omap', from_yaml)


def update_settings_tree(base: ConfigTree, update: ConfigTree) -> ConfigTree:
    """
    For all attributes in "update" override the defaults set in "base"
    or add them to the tree, if they did not exist in "base".

    :param base: default config tree
    :param update: "patch" for the default config tree
    :return: the updated tree
    """
    updated = deepcopy(base)
    for _, key in enumerate(update):
        if type(update[key]) is ConfigTree:
            if key in base:
                updated[key] = update_settings_tree(base[key], update[key])
            else:
                updated[key] = update[key]
        else:
            updated[key] = update[key]
    return updated


def get_configuration(default_filename: str = 'defaults.yml', user_filename: str = 'config.yml') -> ConfigTree:
    """
    gets the current configuration, as specified by YAML files

    :param default_filename: name of the default settings file (relative to configparser.py)
    :param user_filename: name of the user settings file (relative to configparser.py)
    :return: settings tree
    """

    # read defaults
    with open(default_filename, 'r') as file:
        defaults = yaml.load(file)

    with open(user_filename, 'r') as file:
        user_config = yaml.load(file)

    # apply user config over Defaults
    configuration = update_settings_tree(base=defaults, update=user_config)

    return configuration
