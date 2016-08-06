"""Contains the Switch parent class."""
import copy

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("state", "recycle_jitter_count")
class Switch(SystemWideDevice):

    """A switch in a pinball machine."""

    config_section = 'switches'
    collection = 'switches'
    class_label = 'switch'

    def __init__(self, machine, name):
        """Initialise switch."""
        self.hw_switch = None
        super().__init__(machine, name)

        self.deactivation_events = set()
        self.activation_events = set()
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

        self._configured_switch = None

        # register switch so other devices can add handlers to it
        self.machine.switch_controller.register_switch(name)

    def validate_and_parse_config(self, config, is_mode_config):
        """Validate switch config."""
        platform = self.machine.get_platform_sections('switches', getattr(config, "platform", None))
        platform.validate_switch_section(self, config)
        return config

    def _initialize(self):
        self.load_platform_section('switches')

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_secs = self.config['ignore_window_ms'] / 1000.0

        self.hw_switch = self.platform.configure_switch(self.config)

    def get_configured_switch(self):
        """Reconfigure switch."""
        if not self._configured_switch:
            self._configured_switch = ConfiguredHwSwitch(self.hw_switch, {}, self.invert)
        return self._configured_switch


class ConfiguredHwSwitch:

    """Configured hw switch."""

    def __init__(self, hw_switch, config_overwrite, invert):
        """Initialise configured hw switch."""
        self.hw_switch = hw_switch
        self.invert = invert
        self.config = copy.deepcopy(self.hw_switch.config)
        for name, item in config_overwrite.items():
            if item is not None:
                self.config[name] = item

    def __eq__(self, other):
        """Compare two configured switches."""
        return self.hw_switch == other.hw_switch and self.config == other.config

    def __hash__(self):
        """Return id of hw switch and config."""
        return id((self.hw_switch, self.config))


class ReconfiguredSwitch():

    """Reconfigured switch.

    Can overwrite platform specific config parameters and invert.
    """

    def __init__(self, switch, config_switch_overwrite, invert):
        """Initialise reconfigured switch."""
        self._config_overwrite = switch.platform.validate_switch_overwrite_section(switch, config_switch_overwrite)
        self._switch = switch
        self._configured_switch = None
        self._invert = invert

    def __getattr__(self, item):
        """Return parent attributes."""
        return getattr(self._switch, item)

    @property
    def invert(self):
        """Return true if switch is inverted."""
        if bool(self._invert) != bool(self._switch.invert):
            return 1
        else:
            return 0

    def get_configured_switch(self):
        """Return configured hw switch."""
        if not self._configured_switch:
            self._configured_switch = ConfiguredHwSwitch(self.hw_switch, self._config_overwrite, self.invert)
        return self._configured_switch

    @property
    def config(self):
        """Return merged config."""
        config = copy.deepcopy(self._switch.config)
        for name, item in self._config_overwrite.items():
            if item is not None:
                config[name] = item

        return config
