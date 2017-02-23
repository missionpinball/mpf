"""Contains the Device base class."""
import abc

from mpf.core.machine import MachineController
from mpf.core.logging import LogMixin


class Device(LogMixin, metaclass=abc.ABCMeta):

    """Generic parent class of for every hardware device in a pinball machine."""

    config_section = None  # String of the config section name
    collection = None  # String name of the collection
    class_label = None  # String of the friendly name of the device class
    allow_empty_configs = False  # Can a config for this device be empty?

    def __init__(self, machine: MachineController, name: str):
        """Set up default attributes of every device.

        Args:
            machine: The machine controller.
            name: Name of the device in config.
        """
        self.machine = machine
        self.name = name.lower()
        self.tags = []
        self.label = None
        self.platform = None
        self.config = dict()

    @classmethod
    def get_config_spec(cls):
        """Return config spec for this device."""
        return False

    def load_platform_section(self, platform_section: str):
        """Can be called in _initialize to load the platform section.

        Args:
            platform_section: Name of the platform section.
        """
        self.platform = self.machine.get_platform_sections(platform_section, self.config['platform'])

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

        self._configure_device_logging(config)

        return config

    def _configure_device_logging(self, config):

        if config['debug']:
            config['console_log'] = 'full'
            config['file_log'] = 'full'

        self.configure_logging(self.class_label + '.' + self.name,
                               config['console_log'],
                               config['file_log'])

        self.debug_log('Platform Driver: %s', self.platform)
        self.debug_log("Configuring device with settings: '%s'", config)

    def load_config(self, config: dict):
        """Load config.

        Args:
            config: Config for device
        """
        self.config = config

        self.tags = self.config['tags']
        self.label = self.config['label']

    def __repr__(self):
        """Return string representation."""
        return '<{self.class_label}.{self.name}>'.format(self=self)

    # def enable_debugging(self):
    #     """Enable debug logging."""
    #     self.debug_log("Enabling debug logging")
    #     self.debug = True
    #     self._enable_related_device_debugging()
    #
    # def disable_debugging(self):
    #     """Disable debug logging."""
    #     self.debug_log("Disabling debug logging")
    #     self.debug = False
    #     self._disable_related_device_debugging()
    #
    # def _enable_related_device_debugging(self):
    #     pass
    #
    # def _disable_related_device_debugging(self):
    #     pass

    @classmethod
    def get_config_info(cls):
        """Return config collection and config section.

        Returns (str, str): Tuple with (collection, config_section)
        """
        return cls.collection, cls.config_section

    def _initialize(self):
        """Default initialize method."""
        pass
