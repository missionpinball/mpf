""" Contains the base class for flippers."""
# flipper.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device


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

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Flipper.' + name)

        if 'enable_events' not in config:
            config['enable_events'] = {'ball_started': 0}

        if 'disable_events' not in config:
            config['disable_events'] = {'ball_ending': 0,
                                        'tilt': 0,
                                        'slam_tilt': 0}

        super(Flipper, self).__init__(machine, name, config, collection)

        # todo convert to dict
        self.no_hold = False
        self.strength = 100
        self.inverted = False
        self.rules = dict()
        self.platform = None

        self.rules['a'] = False
        self.rules['b'] = False
        self.rules['c'] = False
        self.rules['d'] = False
        self.rules['e'] = False
        self.rules['f'] = False
        self.rules['h'] = False
        self.rules['g'] = False

        if config:
            self.configure(config)

    def configure(self, config=None):
        """Configures the flipper device.

        args:
            config : A dictionary that holds the configuration values which
                specify how this flipper should be configured. If this is None,
                it will use the system config settings that were read in from
                the config files when the machine was reset.
        """
        # Merge in any new changes that were just passed
        if config:
            self.config.update(config)

        self.log.debug("Configuring device with: %s", self.config)

        # todo convert these to objects:
        # config['main_coil']
        # config['activation_switch']
        # config['hold_coil']
        # config['eos_switch']
        # config['use_eos']

        self.flipper_coils = []
        self.flipper_coils.append(self.config['main_coil'])
        if self.config['hold_coil']:
            self.flipper_coils.append(self.config['hold_coil'])

        self.flipper_switches = []
        self.flipper_switches.append(self.config['activation_switch'])
        if self.config['eos_switch']:
            self.flipper_switches.append(self.config['eos_switch'])

        self.platform = self.machine.coils[self.config['main_coil']].platform

    def enable(self, *args, **kwargs):
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
        F.    Disable  Main  Button  inactive
        G.    Disable  Hold  Button  inactive

        One coil, using EOS switch
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        H.    PWM      Main  EOS     active
        F.    Disable  Main  Button  inactive

        Two coils, not using EOS switch:
        Rule  Type     Coil  Switch  Action
        B.    Pulse    Main  Button  active
        D.    Enable   Hold  Button  active
        F.    Disable  Main  Button  inactive
        G.    Disable  Hold  Button  inactive

        One coil, not using EOS switch
        Rule  Type       Coil  Switch  Action
        C.    Pulse/PWM  Main  button  active
        F.    Disable    Main  button  inactive

        Use EOS switch for safety (for platforms that support mutiple switch
        rules). Note that this rule is the letter "i", not a numeral 1.
        I. Enable power if button is active and EOS is not active
        """

        # todo disable first to clear any old rules?

        self.log.debug('Enabling')

        # Apply the proper hardware rules for our config

        if self.config['hold_coil'] and \
                self.config['use_eos'] and \
                self.config['eos_switch']:
            self._enable_flipper_rule_A()
            self._enable_flipper_rule_D()
            self._enable_flipper_rule_E()
            self._enable_flipper_rule_F()
            self._enable_flipper_rule_G()

        elif not self.config['hold_coil'] and \
                self.config['use_eos'] and \
                self.config['eos_switch']:
            self._enable_flipper_rule_A()
            self._enable_flipper_rule_H()
            self._enable_flipper_rule_F()

        elif self.config['hold_coil'] and not self.config['use_eos']:
            self._enable_flipper_rule_B()
            self._enable_flipper_rule_D()
            self._enable_flipper_rule_F()
            self._enable_flipper_rule_G()

        elif not self.config['hold_coil'] and not self.config['use_eos']:
            self._enable_flipper_rule_C()
            self._enable_flipper_rule_F()

            # todo detect bad EOS and program around it

    def enable_no_hold(self):  # todo niy
        """Enables the flippers in 'no hold' mode.

        No Hold is a novelty mode where the flippers to not stay up even when
        the buttons are held in.

        This mode is not yet implemented.
        """
        self.no_hold = True
        self.enable()

    @classmethod
    def invert(self):  # todo niy
        """Enables inverted flippers.

        Inverted flippers is a novelty mode where the left flipper button
        controls the right flippers and vice-versa.

        This mode is not yet implemented.
        """
        self.inverted = True
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

    def disable(self, *args, **kwargs):
        """Disables the flipper.

        This method makes it so the cabinet flipper buttons no longer control
        the flippers. Used when no game is active and when the player has
        tilted.

        """

        if self.flipper_switches:
            self.log.debug("Disabling")
            for switch in self.flipper_switches:
                self.platform.clear_hw_rule(switch)

    def _enable_flipper_rule_A(self):
        """
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        """
        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'],
            sw_activity='active',
            coil_name=self.config['main_coil'],
            coil_action_ms=-1,
            debounced=False)

        self.rules['a'] = True

    def _enable_flipper_rule_B(self):
        """
        Rule  Type     Coil  Switch  Action
        B.    Pulse    Main  Button  active
        """
        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'],
            sw_activity='active',
            coil_name=self.config['main_coil'],
            coil_action_ms=self.machine.coils[self.config['main_coil']].
                config['pulse_ms'],
            pulse_ms=self.machine.coils[self.config['main_coil']].
                config['pulse_ms'],
            debounced=False)

        self.rules['b'] = True

    def _enable_flipper_rule_C(self):
        """
        Rule  Type       Coil  Switch  Action
        C.    Pulse/PWM  Main  button  active
        """
        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'],
            sw_activity='active',
            coil_name=self.config['main_coil'],
            coil_action_ms=-1,
            pulse_ms=self.machine.coils[self.config['main_coil']].
                config['pulse_ms'],
            pwm_on=self.machine.coils[self.config['main_coil']].config['pwm_on'],
            pwm_off=self.machine.coils[self.config['main_coil']].config['pwm_off'],
            debounced=False)

        self.rules['c'] = True

    def _enable_flipper_rule_D(self):
        """
        Rule  Type     Coil  Switch  Action
        D.    Enable   Hold  Button  active
        """
        self.platform.set_hw_rule(
            sw_name=self.config['activation_switch'],
            sw_activity='active',
            coil_name=self.config['hold_coil'],
            coil_action_ms=-1,
            debounced=False)

        self.rules['d'] = True

    def _enable_flipper_rule_E(self):
        """
        Rule  Type     Coil  Switch  Action
        E.    Disable  Main  EOS     active
        """
        self.platform.set_hw_rule(
            sw_name=self.config['eos_switch'],
            sw_activity='active',
            coil_name=self.config['main_coil'],
            coil_action_ms=0,
            debounced=False)

        self.rules['e'] = True

    def _enable_flipper_rule_F(self):
        """
        Rule  Type     Coil  Switch  Action
        F.    Disable  Main  Button  inactive
        """
        if not self.machine.config['platform']['hw_enable_auto_disable']:
            self.platform.set_hw_rule(
                sw_name=self.config['activation_switch'],
                sw_activity='inactive',
                coil_name=self.config['main_coil'],
                coil_action_ms=0,
                debounced=False)

        self.rules['f'] = True

    def _enable_flipper_rule_G(self):
        """
        Rule  Type     Coil  Switch  Action
        G.    Disable  Hold  Button  inactive
        """
        if not self.machine.config['platform']['hw_enable_auto_disable']:
            self.platform.set_hw_rule(
                sw_name=self.config['activation_switch'],
                sw_activity='inactive',
                coil_name=self.config['hold_coil'],
                coil_action_ms=0,
                debounced=False)

        self.rules['g'] = True

    def _enable_flipper_rule_H(self):
        """
        Rule  Type     Coil  Switch  Action
        H.    PWM      Main  EOS     active
        """
        self.platform.set_hw_rule(
            sw_name=self.config['eos_switch'],
            sw_activity='active',
            coil_name=self.config['main_coil'],
            coil_action_ms=-1,
            pwm_on=self.machine.coils[self.config['main_coil']].config['pwm_on'],
            pwm_off=self.machine.coils[self.config['main_coil']].config['pwm_off'])

        self.rules['h'] = True

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
            name=self.config['activation_switch'],
            state=1,
            logical=True)

        if self.rules['c']:  # pulse/pwm main
            coil = self.machine.coils[self.config['main_coil']]
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
            name=self.config['activation_switch'],
            state=0,
            logical=True)

        # disable the flipper coil(s)
        for coil in self.flipper_coils:
            self.machine.coils[coil].disable()



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
