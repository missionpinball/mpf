"""Contains the Device base class."""
import abc

from typing import List, Any, Optional

from mpf.core.machine import MachineController
from mpf.core.logging import LogMixin

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.mode import Mode      # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.platform import BasePlatform    # pylint: disable-msg=cyclic-import,unused-import; # noqa


class Device(LogMixin, metaclass=abc.ABCMeta):

    """Generic parent class of for every hardware device in a pinball machine."""

    # String of the config section name
    config_section = None   # type: str

    # String name of the collection
    collection = None       # type: str

    # String of the friendly name of the device class
    class_label = None      # type: str

    # Can a config for this device be empty?
    allow_empty_configs = False

    __slots__ = ["machine", "name", "tags", "platform", "label", "config"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Set up default attributes of every device.

        Args:
        ----
            machine: The machine controller.
            name: Name of the device in config.
        """
        super().__init__()
        self.machine = machine
        self.name = name
        self.tags = []          # type: List[str]
        self.platform = None    # type: Optional[BasePlatform]
        """List of tags applied to this device."""

        self.label = None       # type: Optional[str]
        self.config = dict()    # type: Any
        """Validated dictionary of this device's settings. Note that this will
        map to the YAML-based config specified in the Config Spec section of
        the User Documentation.
        """

    def __lt__(self, other):
        """Compare two devices."""
        return self.name < other.name

    async def device_added_to_mode(self, mode: "Mode") -> None:
        """Add a device to a running mode.

        Args:
        ----
            mode: Mode which loaded the device
        """
        raise AssertionError("Cannot use device {} in mode {}.".format(self.name, mode.name))

    @classmethod
    def get_config_spec(cls):
        """Return config spec for this device."""
        return False

    def load_platform_section(self, platform_section: str):
        """Can be called in _initialize to load the platform section.

        Args:
        ----
            platform_section: Name of the platform section.
        """
        self.platform = self.machine.get_platform_sections(platform_section, self.config['platform'])

    @classmethod
    def prepare_config(cls, config: dict, is_mode_config: bool) -> dict:
        """Return the config prepared for validation.

        Args:
        ----
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide

        Returns: Prepared config
        """
        del is_mode_config
        return config

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Return the parsed and validated config.

        Args:
        ----
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide
            debug_prefix: Prefix to use when logging.

        Returns: Validated config
        """
        del is_mode_config
        self.machine.config_validator.validate_config(
            self.config_section, config, self.name, "device", prefix=debug_prefix)

        self._configure_device_logging(config)

        return config

    def _configure_device_logging(self, config):

        if config['debug']:
            config['console_log'] = 'full'
            config['file_log'] = 'full'

        self.configure_logging(self.class_label + '.' + self.name,
                               config['console_log'],
                               config['file_log'], url_base=self.class_label)

        self.debug_log("Configuring device with settings: '%s'", config)

    def load_config(self, config: dict):
        """Load config.

        Args:
        ----
            config: Config for device
        """
        self.config = config

        self.tags = self.config['tags']
        self.label = self.config['label']

    def __repr__(self):
        """Return string representation."""
        return '<{self.class_label}.{self.name}>'.format(self=self)

    @classmethod
    def get_config_info(cls):
        """Return config collection and config section.

        Returns (str, str): Tuple with (collection, config_section)
        """
        if not cls.collection or not cls.config_section:
            raise AssertionError("Implement collection and config_section in {}".format(cls))

        return cls.collection, cls.config_section

    async def _initialize(self):
        """initialize device."""
