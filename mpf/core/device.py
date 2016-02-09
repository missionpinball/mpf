""" Contains the Device base class"""

import logging


class Device(object):
    """ Generic parent class of for every hardware device in a pinball machine.

    """

    config_section = None  # String of the config section name
    collection = None  # String name of the collection
    class_label = None  # String of the friendly name of the device class

    def __init__(self, machine, name, config=None, collection=-1,
                 platform_section=None, validate=True):

        self.machine = machine
        self.name = name.lower()
        self.log = logging.getLogger(self.class_label + '.' + self.name)
        self.tags = list()
        self.label = None
        self.debug = False
        self.platform = None
        self.config = dict()

        if validate:
            self.config = self.machine.config_validator.validate_config(
                self.config_section, config, self.name)

        else:
            self.config = config

        if self.config['debug']:
            self.enable_debugging()
            self.log.debug("Configuring device with settings: '%s'", config)

        self.tags = self.config['tags']
        self.label = self.config['label']

        if platform_section:
            self.platform = self.machine.get_platform_sections(platform_section, config['platform'])

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

        # Add this instance to the collection for this type of device
        if collection != -1:
            # Have to use -1 here instead of None to catch an empty collection
            collection[name] = self

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

    @staticmethod
    def create_devices(cls, collection, config, machine, validate=True):
        # if this device class has a device_class_init classmethod, run it now
        if config and hasattr(cls, 'device_class_init'):
            # don't want to use try here in case the called meth has an error
            cls.device_class_init(machine)

        # create the devices

        if config:
            for device in config:

                if not config[device]:
                    raise AssertionError("Device '{}' has an empty config."
                                         .format(device))

                elif type(config[device]) is not dict:
                    raise AssertionError("Device '{}' does not have a valid config."
                                         .format(device))

                cls(machine, device, config[device], collection, validate)

    def device_added_to_mode(self, mode, player):
        # Called when a device is created by a mode
        pass

    def control_events_in_mode(self, mode):
        # Called on mode start if this device has any control events in that mode
        pass

    def remove(self):
        raise NotImplementedError(
            '{} does not have a remove() method'.format(self.name))
