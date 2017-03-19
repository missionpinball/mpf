"""Contains the Switch parent class."""
from typing import Set, TYPE_CHECKING

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.system_wide_device import SystemWideDevice

if TYPE_CHECKING:
    from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
    from mpf.core.platform import SwitchPlatform


@DeviceMonitor("state", "recycle_jitter_count")
class Switch(SystemWideDevice):

    """A switch in a pinball machine."""

    config_section = 'switches'
    collection = 'switches'
    class_label = 'switch'

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise switch."""
        self.hw_switch = None   # type: SwitchPlatformInterface
        self.platform = None    # type: SwitchPlatform
        super().__init__(machine, name)

        self.deactivation_events = set()    # type: Set[str]
        self.activation_events = set()      # type: Set[str]
        self.state = 0
        """ The logical state of a switch. 1 = active, 0 = inactive. This takes
        into consideration the NC or NO settings for the switch."""
        self.hw_state = 0
        """ The physical hardware state of the switch. 1 = active,
        0 = inactive. This is what the actual hardware is reporting and does
        not consider whether a switch is NC or NO."""

        self.invert = 0

        self.recycle_secs = 0
        self.recycle_clear_time = 0
        self.recycle_jitter_count = 0

        # register switch so other devices can add handlers to it
        self.machine.switch_controller.register_switch(name)

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Register handler for duplicate switch number checks."""
        machine.events.add_handler("init_phase_4", cls._check_duplicate_switch_numbers, machine=machine)

    @staticmethod
    def _check_duplicate_switch_numbers(machine, **kwargs):
        del kwargs
        check_set = set()
        for switch in machine.switches:
            key = (switch.platform, switch.hw_switch.number)
            if key in check_set:
                raise AssertionError("Duplicate switch number {} for switch {}".format(switch.hw_switch.number, switch))

            check_set.add(key)

    def validate_and_parse_config(self, config, is_mode_config):
        """Validate switch config."""
        platform = self.machine.get_platform_sections('switches', getattr(config, "platform", None))
        platform.validate_switch_section(self, config)
        self._configure_device_logging(config)
        return config

    def _initialize(self):
        self.platform = self.machine.get_platform_sections('switches', self.config['platform'])

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_secs = self.config['ignore_window_ms'] / 1000.0

        self.hw_switch = self.platform.configure_switch(self.config)

    # pylint: disable-msg=too-many-arguments
    def add_handler(self, callback, state=1, ms=0, return_info=False, callback_kwargs=None):
        """Add switch handler for this switch."""
        return self.machine.switch_controller.add_switch_handler(self.name, callback, state, ms, return_info,
                                                                 callback_kwargs)

    def remove_handler(self, callback, state=1, ms=0):
        """Remove switch handler for this switch."""
        return self.machine.switch_controller.remove_switch_handler(self.name, callback, state, ms)
