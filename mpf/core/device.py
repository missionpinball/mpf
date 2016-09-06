"""Contains the Device base class."""
import abc
import logging

from mpf.core.machine import MachineController


class Device(object, metaclass=abc.ABCMeta):

    """Generic parent class of for every hardware device in a pinball machine."""

    config_section = None  # String of the config section name
    collection = None  # String name of the collection
    class_label = None  # String of the friendly name of the device class

    def __init__(self, machine: MachineController, name: str):
        """Set up default attributes of every device.

        Args:
            machine: The machine controller.
            name: Name of the device in config.
        """
        self.machine = machine
        self.name = name.lower()
        self.log = logging.getLogger(self.class_label + '.' + self.name)
        self.tags = []
        self.label = None
        self.debug = False
        self.platform = None
        self.config = dict()

    def load_platform_section(self, platform_section: str):
        """Can be called in _initialize to load the platform section.

        Args:
            platform_section: Name of the platform section.
        """
        self.platform = self.machine.get_platform_sections(platform_section, self.config['platform'])

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

    def debug_log(self, msg: str, *args, **kwargs):
        """Log to debug if debug is enabled for the device.

        Args:
            msg: Message to log
            *args: args for debug
            **kwargs: kwargs for debug
        """
        if self.debug:
            self.log.debug(msg, *args, **kwargs)

    @classmethod
    def prepare_config(cls, config: dict, is_mode_config: bool) -> dict:
        """Return the config prepared for validation.

        Args:
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide

        Returns: Prepared config
        """
        del is_mode_config
        return config

    def validate_and_parse_config(self, config: dict, is_mode_config: bool) -> dict:
        """Return the parsed and validated config.

        Args:
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide

        Returns: Validated config
        """
        del is_mode_config
        self.machine.config_validator.validate_config(
            self.config_section, config, self.name, "device")
        return config

    def load_config(self, config: dict):
        """Load config.

        Args:
            config: Config for device
        """
        self.config = config

        self.tags = self.config['tags']
        self.label = self.config['label']

        if self.config['debug']:
            self.enable_debugging()
            self.log.debug("Configuring device with settings: '%s'", config)

    def __repr__(self):
        """Return string representation."""
        return '<{self.class_label}.{self.name}>'.format(self=self)

    def enable_debugging(self):
        """Enable debug logging."""
        self.log.debug("Enabling debug logging")
        self.debug = True
        self._enable_related_device_debugging()

    def disable_debugging(self):
        """Disable debug logging."""
        self.log.debug("Disabling debug logging")
        self.debug = False
        self._disable_related_device_debugging()

    def _enable_related_device_debugging(self):
        pass

    def _disable_related_device_debugging(self):
        pass

    @classmethod
    def get_config_info(cls):
        """Return config collection and config section.

        Returns (str, str): Tuple with (collection, config_section)
        """
        return cls.collection, cls.config_section

    def _initialize(self):
        """Default initialize method."""
        pass
