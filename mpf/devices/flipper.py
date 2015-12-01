""" Contains the base class for flippers."""
# flipper.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.device import Device


class Flipper(Device):
    """Represents a flipper in a pinball machine. Subclass of Device.

    Contains several methods for actions that can be performed on this flipper,
    like :meth:`enable`, :meth:`disable`, etc.

    Flippers have several options, including player buttons, EOS swtiches,
    multiple coil options (pulsing, hold coils, etc.)

    More details: http://missionpinball.com/docs/devices/flippers/

    Args:
        machine: A reference to the machine controller instance.
        name: A string of the name you'll refer to this flipper object as.
        config: A dictionary that holds the configuration values which specify
            how this flipper should be configured. If this is None, it will use
            the system config settings that were read in from the config files
            when the machine was reset.
        collection: A reference to the collection list this device will be added
        to.
    """
    config_section = 'flippers'
    collection = 'flippers'
    class_label = 'flipper'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(Flipper, self).__init__(machine, name, config, collection,
                                      validate=validate)

        # todo convert to dict
        self.no_hold = False
        self.strength = 100
        self.inverted = False
        self.rules = dict()

        self.rules['a'] = False
        self.rules['b'] = False
        # self.rules['c'] = False
        self.rules['d'] = False
        self.rules['e'] = False
        self.rules['h'] = False

        self.flipper_coils = []
        self.flipper_coils.append(self.config['main_coil'].name)
        if self.config['hold_coil']:
            self.flipper_coils.append(self.config['hold_coil'].name)

        self.flipper_switches = []
        self.flipper_switches.append(self.config['activation_switch'].name)

        self.platform = self.config['main_coil'].platform

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

        One coil, using EOS switch
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        H.    PWM      Main  EOS     active

        Two coils, not using EOS switch:
        Rule  Type     Coil  Switch  Action
        B.    Pulse    Main  Button  active
        D.    Enable   Hold  Button  active

        One coil, not using EOS switch
        Rule  Type       Coil  Switch  Action
        C.    Pulse/PWM  Main  button  active

        Use EOS switch for safety (for platforms that support mutiple switch
        rules). Note that this rule is the letter "i", not a numeral 1.
        I. Enable power if button is active and EOS is not active
        """

        # todo disable first to clear any old rules?

        self.log.debug('Enabling flipper with config: %s', self.config)

        # Apply the proper hardware rules for our config

        if not self.config['hold_coil']:  # single coil
            self._enable_single_coil_rule()

        elif not self.config['use_eos']:  # two coils, no eos
            self._enable_main_coil_pulse_rule()
            self._enable_hold_coil_rule()

        elif self.config['use_eos']:  # two coils, cutoff main on EOS
            self._enable_main_coil_eos_cutoff_rule()
            self._enable_hold_coil_rule()

        # todo detect bad EOS and program around it

    def enable_no_hold(self):  # todo niy
        """Enables the flippers in 'no hold' mode.

        No Hold is a novelty mode where the flippers to not stay up even when
        the buttons are held in.

        This mode is not yet implemented.
        """
        self.no_hold = True
        self.enable()

    def enable_partial_power(self, percent):  # todo niy
        """Enables flippers which operated at less than full power.

        This is a novelty mode, like "weak flippers" from the Wizard of Oz.

        Args:
            percent: A floating point value between 0 and 1.0 which represents the
                percentage of power the flippers will be enabled at.

        This mode is not yet implemented.

        """
        self.power = percent
        self.enable()

    def disable(self, **kwargs):
        """Disables the flipper.

        This method makes it so the cabinet flipper buttons no longer control
        the flippers. Used when no game is active and when the player has
        tilted.

        """
        if self.flipper_switches:
            self.log.debug("Disabling")
            for switch in self.flipper_switches:
                self.platform.clear_hw_rule(switch)

    def _enable_single_coil_rule(self):
        self.log.debug('Enabling single coil rule')

        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'].name,
            sw_activity=1,
            driver_name=self.config['main_coil'].name,
            driver_action='hold',
            disable_on_release=True,
            **self.config)

        self.rules['a'] = True

    def _enable_main_coil_pulse_rule(self):
        self.log.debug('Enabling main coil pulse rule')

        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'].name,
            sw_activity=1,
            driver_name=self.config['main_coil'].name,
            driver_action='pulse',
            disable_on_release=True,
            **self.config)

        self.rules['b'] = True

    def _enable_hold_coil_rule(self):
        self.log.debug('Enabling hold coil rule')

        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'].name,
            sw_activity=1,
            driver_name=self.config['hold_coil'].name,
            driver_action='hold',
            disable_on_release=True,
            **self.config)

        self.rules['d'] = True

    def _enable_main_coil_eos_cutoff_rule(self):
        self.log.debug('Enabling main coil EOS cutoff rule')

        self.platform.set_hw_rule(
            sw_name=self.config['eos_switch'],
            sw_activity=1,
            driver_name=self.config['main_coil'].name,
            driver_action='disable',
            **self.config)

        self.rules['e'] = True

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

        if self.rules['c']:  # pulse/pwm main
            coil = self.config['main_coil'].config
            coil.pwm(
                on_ms=coil.config['pwm_on'],
                off_ms=coil.config['pwm_off'],
                orig_on_ms=coil.config['pulse_ms']
            )

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
        for coil in self.flipper_coils:
            coil.disable()



# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
