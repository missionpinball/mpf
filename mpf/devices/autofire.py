"""Contains the base class for autofire coil devices."""
from typing import TYPE_CHECKING

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.platform_controller import SwitchRuleSettings, DriverRuleSettings, PulseRuleSettings, HardwareRule

from mpf.core.system_wide_device import SystemWideDevice

if TYPE_CHECKING:
    from mpf.core.machine import MachineController


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

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialise autofire."""
        self._enabled = False
        self._rule = None       # type: HardwareRule
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine.delayRegistry)
        self._ball_search_in_progress = False

    def _initialize(self) -> None:
        if self.config['ball_search_order']:
            self.config['playfield'].ball_search.register(
                self.config['ball_search_order'], self._ball_search, self.name)
        # pulse is handled via rule but add a handler so that we take notice anyway
        self.config['switch'].add_handler(self._hit)

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

    def _hit(self):
        """Rule was triggered."""
        if not self._ball_search_in_progress:
            self.config['playfield'].mark_playfield_active_from_device_action()

    def _ball_search(self, phase, iteration):
        del phase
        del iteration
        self.delay.reset(ms=200, callback=self._ball_search_ignore_done, name="ball_search_ignore_done")
        self._ball_search_in_progress = True
        self.config['coil'].pulse()
        return True

    def _ball_search_ignore_done(self):
        """We no longer expect any fake hits """
        self._ball_search_in_progress = False
