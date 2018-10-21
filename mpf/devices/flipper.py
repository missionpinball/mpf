"""Contains the base class for flippers."""
from typing import List
from typing import Optional

from mpf.core.events import event_handler
from mpf.core.platform_controller import HardwareRule

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.platform_controller import SwitchRuleSettings, DriverRuleSettings, PulseRuleSettings, HoldRuleSettings

from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor(_enabled="enabled")
class Flipper(SystemWideDevice):

    """Represents a flipper in a pinball machine. Subclass of Device.

    Contains several methods for actions that can be performed on this flipper,
    like :meth:`enable`, :meth:`disable`, etc.

    Flippers have several options, including player buttons, EOS swtiches,
    multiple coil options (pulsing, hold coils, etc.)

    Args:
        machine: A reference to the machine controller instance.
        name: A string of the name you'll refer to this flipper object as.
    """

    __slots__ = ["_enabled", "_active_rules", "_sw_flipped"]

    config_section = 'flippers'
    collection = 'flippers'
    class_label = 'flipper'

    def __init__(self, machine, name):
        """Initialise flipper."""
        super().__init__(machine, name)

        self._enabled = False
        self._active_rules = []     # type: List[HardwareRule]
        self._sw_flipped = False

    def _initialize(self):
        if self.config['include_in_ball_search']:
            self.config['playfield'].ball_search.register(
                self.config['ball_search_order'], self._ball_search, self.name)

    @event_handler(1)
    # to prevent multiple rules at the same time we prioritize disable > enable
    def enable(self, **kwargs):
        """Enable the flipper by writing the necessary hardware rules to the hardware controller.

        The hardware rules for coils can be kind of complex given all the
        options, so we've mapped all the options out here. We literally have
        methods to enable the various rules based on the rule letters here,
        which we've implemented below. Keeps it easy to understand. :)

        Note there's a platform feature saved at:
        self.machine.config['platform']['hw_enable_auto_disable']. If True, it
        means that the platform hardware rules will automatically disable a coil
        that has been enabled when the trigger switch is disabled. If False, it
        means the hardware platform needs its own rule to disable the coil when
        the switch is disabled. Methods F and G below check for that feature
        setting and will not be applied to the hardware if it's True.

        Two coils, using EOS switch to indicate the end of the power stroke:
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        D.    Enable   Hold  Button  active
        E.    Disable  Main  EOS     active

        One coil, using EOS switch (not implemented):
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        H.    PWM      Main  EOS     active

        Two coils, not using EOS switch:
        Rule  Type     Coil  Switch  Action
        B.    Pulse    Main  Button  active
        D.    Enable   Hold  Button  active

        One coil, not using EOS switch:
        Rule  Type       Coil  Switch  Action
        C.    Pulse/PWM  Main  button  active

        Use EOS switch for safety (for platforms that support mutiple switch
        rules). Note that this rule is the letter "i", not a numeral 1.
        I. Enable power if button is active and EOS is not active
        """
        del kwargs

        # prevent duplicate enable
        if self._enabled:
            return

        self._enabled = True

        self.debug_log('Enabling flipper with config: %s', self.config)

        # Apply the proper hardware rules for our config

        if self.config['activation_switch']:
            # only add rules if we are using a switch
            if self.config['use_eos']:
                self._enable_main_coil_eos_cutoff_rule()
            elif self.config['hold_coil']:
                self._enable_main_coil_pulse_rule()
            else:
                self._enable_single_coil_rule()

            if self.config['hold_coil']:
                self._enable_hold_coil_rule()

    @event_handler(10)
    # to prevent multiple rules at the same time we prioritize disable > enable
    def disable(self, **kwargs):
        """Disable the flipper.

        This method makes it so the cabinet flipper buttons no longer control
        the flippers. Used when no game is active and when the player has
        tilted.
        """
        del kwargs
        if not self._enabled:
            return

        self.debug_log("Disabling")
        for rule in self._active_rules:
            # disable all rules
            self.machine.platform_controller.clear_hw_rule(rule)

        if self._sw_flipped:
            # disable the coils if activated via sw_flip
            self.sw_release()

        self._active_rules = []

        self._enabled = False

    def _get_pulse_ms(self) -> Optional[int]:
        """Return pulse_ms."""
        pulse_ms = self.config['main_coil_overwrite'].get("pulse_ms", None)
        if self.config['power_setting_name']:
            settings_factor = self.machine.settings.get_setting_value(self.config['power_setting_name'])
            if not pulse_ms:
                pulse_ms = self.machine.config['mpf']['default_pulse_ms']
            return int(pulse_ms * settings_factor)
        else:
            return pulse_ms

    def _get_hold_pulse_ms(self) -> Optional[int]:
        """Return pulse_ms for hold coil."""
        pulse_ms = self.config['hold_coil_overwrite'].get("pulse_ms", None)
        if self.config['power_setting_name']:
            settings_factor = self.machine.settings.get_setting_value(self.config['power_setting_name'])
            if not pulse_ms:
                pulse_ms = self.machine.config['mpf']['default_pulse_ms']
            return int(pulse_ms * settings_factor)
        else:
            return pulse_ms

    def _get_pulse_power(self) -> Optional[float]:
        """Return pulse_power."""
        pulse_power = self.config['main_coil_overwrite'].get("pulse_power", None)
        return pulse_power

    def _get_hold_pulse_power(self) -> Optional[float]:
        """Return pulse_power for hold coil."""
        pulse_power = self.config['hold_coil_overwrite'].get("pulse_power", None)
        return pulse_power

    def _get_hold_power(self) -> Optional[float]:
        """Return hold_power."""
        hold_power = self.config['main_coil_overwrite'].get("hold_power", None)
        return hold_power

    def _enable_single_coil_rule(self):
        self.debug_log('Enabling single coil rule')

        rule = self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_rule(
            SwitchRuleSettings(switch=self.config['activation_switch'], debounce=False, invert=False),
            DriverRuleSettings(driver=self.config['main_coil'], recycle=False),
            PulseRuleSettings(duration=self._get_pulse_ms(), power=self._get_pulse_power()),
            HoldRuleSettings(power=self._get_hold_power())
        )
        self._active_rules.append(rule)

    def _enable_main_coil_pulse_rule(self):
        self.debug_log('Enabling main coil pulse rule')

        rule = self.machine.platform_controller.set_pulse_on_hit_and_release_rule(
            SwitchRuleSettings(switch=self.config['activation_switch'], debounce=False, invert=False),
            DriverRuleSettings(driver=self.config['main_coil'], recycle=False),
            PulseRuleSettings(duration=self._get_pulse_ms(), power=self._get_pulse_power())
        )
        self._active_rules.append(rule)

    def _enable_hold_coil_rule(self):
        self.debug_log('Enabling hold coil rule')

        rule = self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_rule(
            SwitchRuleSettings(switch=self.config['activation_switch'], debounce=False, invert=False),
            DriverRuleSettings(driver=self.config['hold_coil'], recycle=False),
            PulseRuleSettings(duration=self._get_hold_pulse_ms(), power=self._get_hold_pulse_power()),
            HoldRuleSettings(power=self._get_hold_power())
        )
        self._active_rules.append(rule)

    def _enable_main_coil_eos_cutoff_rule(self):
        self.debug_log('Enabling main coil EOS cutoff rule')

        rule = self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            SwitchRuleSettings(switch=self.config['activation_switch'], debounce=False, invert=False),
            SwitchRuleSettings(switch=self.config['eos_switch'], debounce=False, invert=False),
            DriverRuleSettings(driver=self.config['main_coil'], recycle=False),
            PulseRuleSettings(duration=self._get_hold_pulse_ms(), power=self._get_hold_pulse_power()),
            HoldRuleSettings(power=self._get_hold_power())
        )
        self._active_rules.append(rule)

    @event_handler(6)
    def sw_flip(self, **kwargs):
        """Activate the flipper via software as if the flipper button was pushed.

        This is needed because the real flipper activations are handled in
        hardware, so if you want to flip the flippers with the keyboard or OSC
        interfaces, you have to call this method.

        Note this method will keep this flipper enabled until you call
        sw_release().
        """
        del kwargs
        if not self._enabled:
            return

        self._sw_flipped = True

        if self.config['hold_coil']:
            self.config['main_coil'].pulse()
            self.config['hold_coil'].enable()
        else:
            self.config['main_coil'].enable()

    @event_handler(5)
    def sw_release(self, **kwargs):
        """Deactive the flipper via software as if the flipper button was released.

        See the documentation for sw_flip() for details.
        """
        del kwargs
        self._sw_flipped = False

        # disable the flipper coil(s)
        self.config['main_coil'].disable()

        if self.config['hold_coil']:
            self.config['hold_coil'].disable()

    def _ball_search(self, phase, iteration):
        del phase
        del iteration
        self.sw_flip()
        self.machine.delay.add(self.config['ball_search_hold_time'],
                               self.sw_release,
                               'flipper_{}_ball_search'.format(self.name))
        return True
