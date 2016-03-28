""" Contains the base class for flippers."""
from mpf.devices.driver import ReconfiguredDriver

from mpf.core.system_wide_device import SystemWideDevice


class Flipper(SystemWideDevice):
    """Represents a flipper in a pinball machine. Subclass of Device.

    Contains several methods for actions that can be performed on this flipper,
    like :meth:`enable`, :meth:`disable`, etc.

    Flippers have several options, including player buttons, EOS swtiches,
    multiple coil options (pulsing, hold coils, etc.)

    More details: http://missionpinball.com/docs/devices/flippers/

    Args:
        machine: A reference to the machine controller instance.
        name: A string of the name you'll refer to this flipper object as.
    """
    config_section = 'flippers'
    collection = 'flippers'
    class_label = 'flipper'

    def __init__(self, machine, name):
        super().__init__(machine, name)

        self.flipper_switches = []
        self.main_coil = None
        self.hold_coil = None

    def _initialize(self):
        self.flipper_switches.append(self.config['activation_switch'].name)
        self.platform = self.config['main_coil'].platform
        self.main_coil = ReconfiguredDriver(self.config['main_coil'], self.config)

        if self.config['hold_coil']:
            self.hold_coil = ReconfiguredDriver(self.config['hold_coil'], self.config)

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

    def enable(self, **kwargs):
        """Enables the flipper by writing the necessary hardware rules to the
        hardware controller.

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

        # todo disable first to clear any old rules?

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
        """Disables the flipper.

        This method makes it so the cabinet flipper buttons no longer control
        the flippers. Used when no game is active and when the player has
        tilted.

        """
        del kwargs
        if self.flipper_switches:
            self.log.debug("Disabling")
            for switch in self.flipper_switches:
                self.platform.clear_hw_rule(switch)

    def _enable_single_coil_rule(self):
        self.log.debug('Enabling single coil rule')

        self.main_coil.set_pulse_on_hit_and_enable_and_release_rule(self.config['activation_switch'])

#        self.platform.set_hw_rule(
#                sw_name=self.config['activation_switch'].name,
#                sw_activity=1,
#                driver_name=self.config['main_coil'].name,
#                driver_action='hold',
#                disable_on_release=True,
#                **self.config)

    def _enable_main_coil_pulse_rule(self):
        self.log.debug('Enabling main coil pulse rule')

        self.main_coil.set_pulse_on_hit_and_release_rule(self.config['activation_switch'])

#        self.platform.set_hw_rule(
#                sw_name=self.config['activation_switch'].name,
#                sw_activity=1,
#                driver_name=self.config['main_coil'].name,
#                driver_action='pulse',
#                disable_on_release=True,
#                **self.config)

    def _enable_hold_coil_rule(self):
        self.log.debug('Enabling hold coil rule')

        self.platform.set_hw_rule(
                sw_name=self.config['activation_switch'].name,
                sw_activity=1,
                driver_name=self.config['hold_coil'].name,
                driver_action='hold',
                disable_on_release=True,
                **self.config)

    def _enable_main_coil_eos_cutoff_rule(self):
        self.log.debug('Enabling main coil EOS cutoff rule')

        # TODO: did that ever work? only a disable rule?

        self.platform.set_hw_rule(
                sw_name=self.config['eos_switch'],
                sw_activity=1,
                driver_name=self.config['main_coil'].name,
                driver_action='disable',
                **self.config)

    def sw_flip(self):
        """Activates the flipper via software as if the flipper button was
        pushed.

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
        """Deactives the flipper via software as if the flipper button was
        released. See the documentation for sw_flip() for details.
        """

        # Send the activation switch release to the switch controller
        self.machine.switch_controller.process_switch(
                name=self.config['activation_switch'].name,
                state=0,
                logical=True)

        # disable the flipper coil(s)
        self.config['main_coil'].disable()
