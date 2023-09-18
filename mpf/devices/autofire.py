"""Contains the base class for autofire coil devices."""
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.platform_controller import SwitchRuleSettings, DriverRuleSettings, PulseRuleSettings, HardwareRule

from mpf.core.system_wide_device import SystemWideDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import
    from typing import List, Optional  # pylint: disable-msg=cyclic-import,unused-import


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
    collection = 'autofire_coils'
    class_label = 'autofire'

    __slots__ = ["_enabled", "_rule", "delay", "_ball_search_in_progress", "_timeout_watch_time", "_timeout_max_hits",
                 "_timeout_disable_time", "_timeout_hits"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """initialize autofire."""
        self._enabled = False
        self._rule = None       # type: Optional[HardwareRule]
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine)
        self._ball_search_in_progress = False
        self._timeout_watch_time = None
        self._timeout_max_hits = None
        self._timeout_disable_time = None
        self._timeout_hits = []     # type: List[float]

    async def _initialize(self):
        await super()._initialize()
        if self.config['ball_search_order']:
            self.config['playfield'].ball_search.register(
                self.config['ball_search_order'], self._ball_search, self.name)
        # pulse is handled via rule but add a handler so that we take notice anyway
        self.config['switch'].add_handler(self._hit)
        if self.config['timeout_watch_time']:
            self._timeout_watch_time = self.config['timeout_watch_time'] / 1000
            self._timeout_max_hits = self.config['timeout_max_hits']
            self._timeout_disable_time = self.config['timeout_disable_time']

        if '{}_active'.format(self.config['playfield'].name) in self.config['switch'].tags:
            self.raise_config_error(
                "Autofire device '{}' uses switch '{}' which has a "
                "'{}_active' tag. This is handled internally by the device. Remove the "
                "redundant '{}_active' tag from that switch.".format(
                    self.name, self.config['switch'].name, self.config['playfield'].name,
                    self.config['playfield'].name), 1)

    @event_handler(1)
    def event_enable(self, **kwargs):
        """Handle enable control event.

        To prevent multiple rules at the same time we prioritize disable > enable.
        """
        del kwargs
        self.enable()

    def enable(self):
        """Enable the autofire device.

        This causes the coil to respond to the switch hits. This is typically
        called when a ball starts to enable the slingshots, pops, etc.

        Note that there are several options for both the coil and the switch
        which can be incorporated into this rule, including recycle times,
        switch debounce, reversing the switch (fire the coil when the switch
        goes inactive), etc. These rules vary by hardware platform. See the
        user documentation for the hardware platform for details.

        Args:
        ----
            **kwargs: Not used, just included so this method can be used as an
                event callback.

        """
        if self._enabled:
            return
        self._enabled = True

        self.debug_log("Enabling")

        if self.config['coil_overwrite'].get('recycle', None) is not None:
            # if coil_overwrite is set use it
            recycle = self.config['coil_overwrite']['recycle']
        else:
            # otherwise load the default from the coil and turn None to True
            recycle = self.config['coil'].config['default_recycle'] in (True, None)

        if self.config['switch_overwrite'].get('debounce', None) is not None:
            # if switch_overwrite is set use it
            debounce = self.config['switch_overwrite']['debounce'] == "normal"
        else:
            # otherwise load the default from the switch and turn auto into False
            debounce = self.config['switch'].config['debounce'] == "normal"

        if not self.config['coil_pulse_delay']:
            self._rule = self.machine.platform_controller.set_pulse_on_hit_rule(
                SwitchRuleSettings(switch=self.config['switch'], debounce=debounce,
                                   invert=self.config['reverse_switch']),
                DriverRuleSettings(driver=self.config['coil'], recycle=recycle),
                PulseRuleSettings(duration=self.config['coil_overwrite'].get('pulse_ms', None),
                                  power=self.config['coil_overwrite'].get('pulse_power', None))
            )
        else:
            self._rule = self.machine.platform_controller.set_delayed_pulse_on_hit_rule(
                SwitchRuleSettings(switch=self.config['switch'], debounce=debounce,
                                   invert=self.config['reverse_switch']),
                DriverRuleSettings(driver=self.config['coil'], recycle=recycle),
                self.config['coil_pulse_delay'],
                PulseRuleSettings(duration=self.config['coil_overwrite'].get('pulse_ms', None),
                                  power=self.config['coil_overwrite'].get('pulse_power', None))
            )

    @event_handler(10)
    def event_disable(self, **kwargs):
        """Handle disable control event.

        To prevent multiple rules at the same time we prioritize disable > enable.
        """
        del kwargs
        self.disable()

    def disable(self):
        """Disable the autofire device.

        This is typically called at the end of a ball and when a tilt event
        happens.

        Args:
        ----
            **kwargs: Not used, just included so this method can be used as an
                event callback.

        """
        self.delay.remove("_timeout_enable_delay")

        if not self._enabled:
            return
        self._enabled = False

        self.debug_log("Disabling")
        self.machine.platform_controller.clear_hw_rule(self._rule)

    def _hit(self):
        """Rule was triggered."""
        if not self._enabled:
            return
        if not self._ball_search_in_progress:
            self.config['playfield'].mark_playfield_active_from_device_action()
        if self._timeout_watch_time:
            current_time = self.machine.clock.get_time()
            self._timeout_hits = [t for t in self._timeout_hits if t > current_time - self._timeout_watch_time / 1000.0]
            self._timeout_hits.append(current_time)

            if len(self._timeout_hits) >= self._timeout_max_hits:
                self.disable()
                self.delay.add(self._timeout_disable_time, self.enable, "_timeout_enable_delay")

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
