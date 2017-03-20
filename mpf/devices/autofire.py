"""Contains the base class for autofire coil devices."""
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.platform_controller import SwitchRuleSettings, DriverRuleSettings, PulseRuleSettings

from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor(_enabled="enabled")
class AutofireCoil(SystemWideDevice):

    """Coils in the pinball machine which should fire automatically based on switch hits using hardware switch rules.

    autofire_coils are used when you want the coils to respond "instantly"
    without waiting for the lag of the python game code running on the host
    computer.

    Examples of autofire_coils are pop bumpers, slingshots, and flippers.

    Args: Same as Device.
    """

    config_section = 'autofire_coils'
    collection = 'autofires'
    class_label = 'autofire'

    def __init__(self, machine, name):
        """Initialise autofire."""
        self._enabled = False
        self._rule = None
        super().__init__(machine, name)

    def _initialize(self):
        if self.config['ball_search_order']:
            self.config['playfield'].ball_search.register(
                self.config['ball_search_order'], self._ball_search, self.name)

    @event_handler(10)
    def enable(self, **kwargs):
        """Enable the autofire coil rule."""
        del kwargs

        if self._enabled:
            return
        self._enabled = True

        self.debug_log("Enabling")

        recycle = True if self.config['coil_overwrite'].get('recycle', None) in (True, None) else False
        debounce = False if self.config['switch_overwrite'].get('debounce', None) in (None, "quick") else True

        self._rule = self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.config['switch'], debounce=debounce,
                               invert=self.config['reverse_switch']),
            DriverRuleSettings(driver=self.config['coil'], recycle=recycle),
            PulseRuleSettings(duration=self.config['coil_overwrite'].get('pulse_ms', None),
                              power=self.config['coil_overwrite'].get('pulse_power', None))
        )

    @event_handler(1)
    def disable(self, **kwargs):
        """Disable the autofire coil rule."""
        del kwargs

        if not self._enabled:
            return
        self._enabled = False

        self.debug_log("Disabling")
        self.machine.platform_controller.clear_hw_rule(self._rule)

    def _ball_search(self, phase, iteration):
        del phase
        del iteration
        self.config['coil'].pulse()
        return True
