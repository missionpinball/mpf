"""Contains the base class for autofire coil devices."""
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.platform_controller import SwitchRuleSettings, DriverRuleSettings, PulseRuleSettings, HardwareRule

from mpf.core.system_wide_device import SystemWideDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController


@DeviceMonitor(_enabled="enabled")
class AutofireCoil(SystemWideDevice):

    """Autofire coils which fire based on switch hits with a hardware rule.

    Coils in the pinball machine which should fire automatically based on
    switch hits using defined hardware switch rules.

    Autofire coils work with rules written to the hardware pinball controller
    that allow them to respond "instantly" to switch hits versus waiting for
    the lag of USB and the host computer.

    Examples of Autofire Coils are pop bumpers, slingshots, and kicking
    targets. (Flippers use the same autofire rules under the hood, but flipper
    devices have their own device type in MPF.

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
        if self.config['enable_timeouts']:
            self._timeout_watch_time = self.config['timeout_watch_time']/1000
            self._timeout_max_hits = self.config['timeout_max_hits']
            self._timeout_disable_time = self.config['timeout_disable_time']/1000
            self._timeout_hits = []
            from time import time as _time
            from threading import Timer as _Timer

    @event_handler(10)
    def enable(self, **kwargs):
        """Enable the autofire device.

        This causes the coil to respond to the switch hits. This is typically
        called when a ball starts to enable the slingshots, pops, etc.

        Note that there are several options for both the coil and the switch
        which can be incorporated into this rule, including recycle times,
        switch debounce, reversing the switch (fire the coil when the switch
        goes inactive), etc. These rules vary by hardware platform. See the
        user documentation for the hardware platform for details.

        Args:
            **kwargs: Not used, just included so this method can be used as an
                event callback.

        """
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
        """Disable the autofire device.

        This is typically called at the end of a ball and when a tilt event
        happens.

        Args:
            **kwargs: Not used, just included so this method can be used as an
                event callback.

        """
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
        if self.config['enable_timeouts']:
            self._timeout_hits.append(_time())
            while True:
                if self._timeout_hits[-1]-self._timeout_hits[0]>self._timeout_watch_time:
                    self._timeout_hits.pop(0)
                else:
                    break
            if len(self._timeout_hits)>self._timeout_max_hits:
                self.disable()
                _timeout_timer=_Timer(self._timeout_disable_time,self.enable)
                _timeout_timer.start()

    def _ball_search(self, phase, iteration):
        del phase
        del iteration
        self.delay.reset(ms=200, callback=self._ball_search_ignore_done, name="ball_search_ignore_done")
        self._ball_search_in_progress = True
        self.config['coil'].pulse()
        return True

    def _ball_search_ignore_done(self):
        """We no longer expect any fake hits."""
        self._ball_search_in_progress = False
