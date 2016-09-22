"""Contains the base class for flippers."""
import copy

from mpf.core.device_monitor import DeviceMonitor

from mpf.devices.driver import ReconfiguredDriver

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.switch import ReconfiguredSwitch


@DeviceMonitor("_enabled")
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

    config_section = 'flippers'
    collection = 'flippers'
    class_label = 'flipper'

    def __init__(self, machine, name):
        """Initialise flipper."""
        super().__init__(machine, name)

        self.main_coil = None
        self.hold_coil = None
        self.switch = None
        self.eos_switch = None
        self._enabled = False

    def _initialize(self):
        if "debounce" not in self.config['switch_overwrite']:
            self.config['switch_overwrite']['debounce'] = "quick"
        if "debounce" not in self.config['eos_switch_overwrite']:
            self.config['eos_switch_overwrite']['debounce'] = "quick"

        self.platform = self.config['main_coil'].platform

        self.switch = ReconfiguredSwitch(self.config['activation_switch'], self.config['switch_overwrite'], False)
        self._reconfigure_drivers()
        if self.config['eos_switch']:
            self.eos_switch = ReconfiguredSwitch(self.config['eos_switch'], self.config['eos_switch_overwrite'], False)

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

        if self.config['power_setting_name']:
            self.machine.events.add_handler("machine_var_{}".format(self.config['power_setting_name']),
                                            self._power_changed)

    def _reconfigure_drivers(self):
        self.main_coil = self._reconfigure_driver(self.config['main_coil'], self.config['main_coil_overwrite'])
        if self.config['hold_coil']:
            self.hold_coil = self._reconfigure_driver(self.config['hold_coil'], self.config['hold_coil_overwrite'])

    def _reconfigure_driver(self, driver, overwrite_config):
        if self.config['power_setting_name']:
            overwrite_config = copy.deepcopy(overwrite_config)
            pulse_ms = driver.config.get(
                "pulse_ms", overwrite_config.get("pulse_ms",self.machine.config['mpf']['default_pulse_ms']))
            settings_factor = self.machine.settings.get_setting_value(self.config['power_setting_name'])
            overwrite_config['pulse_ms'] = int(pulse_ms * settings_factor)
            self.log.info("Configuring driver %s with a pulse time of %s ms for flipper",
                          driver.name, overwrite_config['pulse_ms'])
        return ReconfiguredDriver(driver, overwrite_config)

    def _power_changed(self, **kwargs):
        del kwargs
        self._reconfigure_drivers()

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

        self.log.debug('Enabling flipper with config: %s', self.config)

        # Apply the proper hardware rules for our config

        if not self.config['hold_coil']:  # single coil
            self._enable_single_coil_rule()

        elif not self.config['use_eos']:  # two coils, no eos
            self._enable_main_coil_pulse_rule()
            self._enable_hold_coil_rule()

        else:  # two coils, cutoff main on EOS
            self._enable_main_coil_eos_cutoff_rule()
            self._enable_hold_coil_rule()

            # todo detect bad EOS and program around it

    def disable(self, **kwargs):
        """Disable the flipper.

        This method makes it so the cabinet flipper buttons no longer control
        the flippers. Used when no game is active and when the player has
        tilted.
        """
        del kwargs
        self.log.debug("Disabling")
        self.main_coil.clear_hw_rule(self.switch)
        if self.eos_switch:
            self.main_coil.clear_hw_rule(self.eos_switch)

        if self.hold_coil:
            self.hold_coil.clear_hw_rule(self.switch)

        self._enabled = False

    def _enable_single_coil_rule(self):
        self.log.debug('Enabling single coil rule')

        self.main_coil.set_pulse_on_hit_and_enable_and_release_rule(self.switch)

    def _enable_main_coil_pulse_rule(self):
        self.log.debug('Enabling main coil pulse rule')

        self.main_coil.set_pulse_on_hit_and_release_rule(self.switch)

    def _enable_hold_coil_rule(self):
        self.log.debug('Enabling hold coil rule')

        # TODO: why are we pulsing the hold coil?

        self.hold_coil.set_pulse_on_hit_and_enable_and_release_rule(self.switch)

    def _enable_main_coil_eos_cutoff_rule(self):
        self.log.debug('Enabling main coil EOS cutoff rule')

        self.main_coil.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            self.switch, self.eos_switch)

    def sw_flip(self):
        """Activate the flipper via software as if the flipper button was pushed.

        This is needed because the real flipper activations are handled in
        hardware, so if you want to flip the flippers with the keyboard or OSC
        interfaces, you have to call this method.

        Note this method will keep this flipper enabled until you call
        sw_release().
        """
        # todo add support for other types of flipper coils
        # Send the activation switch press to the switch controller
        self.machine.switch_controller.process_switch(
            name=self.config['activation_switch'].name,
            state=1,
            logical=True)

        self.config['main_coil'].enable()

    def sw_release(self):
        """Deactive the flipper via software as if the flipper button was released.

        See the documentation for sw_flip() for details.
        """
        # Send the activation switch release to the switch controller
        self.machine.switch_controller.process_switch(
            name=self.config['activation_switch'].name,
            state=0,
            logical=True)

        # disable the flipper coil(s)
        self.config['main_coil'].disable()
