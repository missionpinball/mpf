""" Contains the Device base class"""

import logging


class Device(object):
    """ Generic parent class of for every hardware device in a pinball machine.

    """

    config_section = None  # String of the config section name
    collection = None  # String name of the collection
    class_label = None  # String of the friendly name of the device class

    def __init__(self, machine, name):

        self.machine = machine
        self.name = name.lower()
        self.log = logging.getLogger(self.class_label + '.' + self.name)
        self.tags = list()
        self.label = None
        self.debug = False
        self.platform = None
        self.config = dict()

        self.tags = []
        self.label = []

    def load_platform_section(self, platform_section):
        # can be called in _initialize to load the platform section
        self.platform = self.machine.get_platform_sections(platform_section, self.config['platform'])

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

    def debug_log(self, msg, *args, **kwargs):
        # Logs to debug if debug is enabled for the device
        if self.debug:
            self.log.debug(msg, args, kwargs)

    def prepare_config(self, config, is_mode_config):
        del is_mode_config
        # returns the prepared config
        return config

    def load_config(self, config):
        self.config = config

        self.tags = self.config['tags']
        self.label = self.config['label']

        if self.config['debug']:
            self.enable_debugging()
            self.log.debug("Configuring device with settings: '%s'", config)

    def __repr__(self):
        return '<{self.class_label}.{self.name}>'.format(self=self)

    def enable_debugging(self):
        self.log.debug("Enabling debug logging")
        self.debug = True
        self._enable_related_device_debugging()

    def disable_debugging(self):
        self.log.debug("Disabling debug logging")
        self.debug = False
        self._disable_related_device_debugging()

    def _enable_related_device_debugging(self):
        pass

    def _disable_related_device_debugging(self):
        pass

    @classmethod
    def get_config_info(cls):
        return cls.collection, cls.config_section

    def _initialize(self):
        # default initialize method
        pass
