""" Parent contains the base class for diverter devices."""
# diverter.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing


class Diverter(Device):
    """Represents a diverter in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'Diverters'
    collection = 'diverter'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Diverter.' + name)
        super(Diverter, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        # Attributes
        self.active = False
        self.enabled = False
        #self.remaining_activations = -1

        # configure defaults:
        if 'type' not in self.config:
            self.config['type'] = 'pulse'  # default to pulse to not fry coils
        if 'activation_time' not in self.config:
            self.config['activation_time'] = 0
        if 'activation_switches' in self.config:
            self.config['activation_switches'] = self.machine.string_to_list(
                self.config['activation_switches'])
        else:
            self.config['activation_switches'] = list()

        if 'disable_switches' in self.config:
            self.config['disable_switches'] = self.machine.string_to_list(
                self.config['disable_switches'])
        else:
            self.config['disable_switches'] = list()

        if 'deactivation_switches' in self.config:
            self.config['deactivation_switches'] = self.machine.string_to_list(
                self.config['deactivation_switches'])
        else:
            self.config['deactivation_switches'] = list()

        if 'activation_coil' in self.config:
            self.config['activation_coil'] = (
                self.machine.coils[self.config['activation_coil']])

        if 'deactivation_coil' in self.config:
            self.config['deactivation_coil'] = (
                self.machine.coils[self.config['deactivation_coil']])
        else:
            self.config['deactivation_coil'] = None

        if 'targets_when_active' in self.config:
            self.config['targets_when_active'] = self.machine.string_to_list(
                self.config['targets_when_active'])
        else:
            self.config['targets_when_active'] = ['playfield']

        if 'targets_when_inactive' in self.config:
            self.config['targets_when_inactive'] = self.machine.string_to_list(
                self.config['targets_when_inactive'])
        else:
            self.config['targets_when_inactive'] = ['playfield']

        if 'feeder_devices' in self.config:
            self.config['feeder_devices'] = self.machine.string_to_list(
                self.config['feeder_devices'])
        else:
            self.config['feeder_devices'] = list()

        # Create a list of ball device objects when active and inactive. We need
        # this because ball eject attempts pass the target device as an object
        # rather than by name.

        self.config['active_objects'] = list()
        self.config['inactive_objects'] = list()

        for target_device in self.config['targets_when_active']:
            if target_device == 'playfield':
                self.config['active_objects'].append('playfield')
            else:
                self.config['active_objects'].append(
                    self.machine.balldevices[target_device])

        for target_device in self.config['targets_when_inactive']:
            if target_device == 'playfield':
                self.config['inactive_objects'].append('playfield')
            else:
                self.config['inactive_objects'].append(
                    self.machine.balldevices[target_device])

        # convert the activation_time to ms
        self.config['activation_time'] = Timing.string_to_ms(self.config['activation_time'])

        # register for events
        for event in self.config['enable_events']:
            self.machine.events.add_handler(event, self.enable)

        for event in self.config['disable_events']:
            self.machine.events.add_handler(event, self.disable)

        # register for feeder device eject events
        for feeder_device in self.config['feeder_devices']:
            self.machine.events.add_handler('balldevice_' + feeder_device +
                                            '_ball_eject_attempt',
                                            self._feeder_eject_attempt)

        # register for deactivation switches
        for switch in self.config['deactivation_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch, self.deactivate)

        # register for disable switches:
        for switch in self.config['disable_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch, self.disable)

    def enable(self, auto=False, activations=-1, **kwargs):
        """Enables this diverter.

        Args:
            auto: Boolean value which is used to indicate whether this
                diverter enabled itself automatically. This is passed to the
                event which is posted.
            activations: Integer of how many times you'd like this diverter to
                activate before it will automatically disable itself. Default is
                -1 which is unlimited.

        If an 'activation_switches' is configured, then this method writes a
        hardware autofire rule to the pinball controller which fires the
        diverter coil when the switch is activated.

        If no `activation_switches` is specified, then the diverter is activated
        immediately.
        """

        self.enabled = True

        self.machine.events.post('diverter_' + self.name + '_enabling',
                                 auto=auto)

        if self.config['activation_switches']:
            self.enable_hw_switches()
        else:
            self.activate()

    def disable(self, auto=False, **kwargs):
        """Disables this diverter.

        This method will remove the hardware rule if this diverter is activated
        via a hardware switch.

        Args:
            auto: Boolean value which is used to indicate whether this
                diverter disabled itself automatically. This is passed to the
                event which is posted.
            **kwargs: This is here because this disable method is called by
                whatever event the game programmer specifies in their machine
                configuration file, so we don't know what event that might be
                or whether it has random kwargs attached to it.
        """

        self.enabled = False

        self.machine.events.post('diverter_' + self.name + '_disabling',
                                 auto=auto)

        self.log.debug("Disabling Diverter")
        if self.config['activation_switches']:
            self.disable_hw_switch()
        else:
            self.deactivate()

    def activate(self):
        """Physically activates this diverter's coil."""
        self.log.debug("Activating Diverter")

        self.active = True

        #if self.remaining_activations > 0:
        #    self.remaining_activations -= 1

        self.machine.events.post('diverter_' + self.name + '_activating')
        if self.config['type'] == 'pulse':
            self.config['activation_coil'].pulse()
        elif self.config['type'] == 'hold':
            self.config['activation_coil'].enable()
            self.schedule_deactivation()

    def deactivate(self):
        """Deactivates this diverter.

        This method will disable the activation_coil, and (optionally) if it's
        configured with a deactivation coil, it will pulse it.
        """
        self.log.debug("Deactivating Diverter")

        self.active = False

        self.machine.events.post('diverter_' + self.name + '_deactivating')
        self.config['activation_coil'].disable()

        if self.config['deactivation_coil']:
            self.config['deactivation_coil'].pulse()

        #if self.remaining_activations != 0:
        #    self.enable()
            # todo this will be weird if the diverter is enabled without a hw
            # switch.. wonder if we should check for that here?

    def schedule_deactivation(self, time=None):
        """Schedules a delay to deactivate this diverter.

        Args:
            time: The MPF string time of how long you'd like the delay before
                deactivating the diverter. Default is None which means it uses
                the 'activation_time' setting configured for this diverter. If
                there is no 'activation_time' setting and no delay is passed,
                it will disable the diverter immediately.
        """

        if time is not None:
            delay = Timing.string_to_ms(time)

        elif self.config['activation_time']:
            delay = self.config['activation_time']

        if delay:
            self.delay.add('disable_held_coil', delay, self.disable_held_coil)
        else:
            self.disable_held_coil()

    def enable_hw_switches(self):
        """Enables the hardware switch rule which causes this diverter to
        activate when the switch is hit.

        This is typically used for diverters on loops and ramps where you don't
        want the diverter to phsyically activate until the ramp entry switch is
        activated.

        If this diverter is configured with a activation_time, this method will
        also set switch handlers which will set a delay to deactivate the
        diverter once the activation activation_time expires.

        If this diverter is configured with a deactivation switch, this method
        will set up the switch handlers to deactivate the diverter when the
        deactivation switch is activated.
        """
        self.log.debug("Enabling Diverter for hw switch: %s",
                       self.config['activation_switches'])

        if self.config['type'] == 'hold':

            for switch in self.config['activation_switches']:

                self.machine.platform.set_hw_rule(
                    sw_name=switch,
                    sw_activity='active',
                    coil_name=self.config['activation_coil'].name,
                    coil_action_ms=-1,
                    pulse_ms=self.config['activation_coil'].config['pulse_ms'],
                    pwm_on=self.config['activation_coil'].config['pwm_on'],
                    pwm_off=self.config['activation_coil'].config['pwm_off'],
                    debounced=False)

                # If there's a activation_time then we need to watch for the hw
                # switch to be activated so we can disable the diverter

                if self.config['activation_time']:
                    self.machine.switch_controller.add_switch_handler(
                        switch,
                        self.schedule_deactivation)

        elif self.config['type'] == 'pulse':

            for switch in self.config['activation_switches']:

                self.machine.platform.set_hw_rule(
                    sw_name=switch,
                    sw_activity='active',
                    coil_name=self.config['activation_coil'].name,
                    coil_action_ms=self.config['activation_coil'].config['pulse_ms'],
                    pulse_ms=self.config['activation_coil'].config['pulse_ms'],
                    debounced=False)

    def disable_hw_switch(self):
        """Removes the hardware rule to disable the hardware activation switch
        for this diverter.
        """

        for switch in self.config['activation_switches']:
            self.machine.platform.clear_hw_rule(switch)

        # todo this should not clear all the rules for this switch

    def disable_held_coil(self):
        """Physically disables the coil holding this diverter open."""
        self.config['activation_coil'].disable()

    def _feeder_eject_attempt(self, target, **kwargs):
        # Event handler which is called when one of this diverter's feeder
        # devices attempts to eject a ball. This is what allows this diverter
        # to get itself in the right position to send the ball to where it needs
        # to go.

        # Since the 'target' kwarg is going to be an object, not a name, we need
        # to figure out if this object is one of the targets of this diverter.

        self.log.debug("Feeder device eject attempt for target: %s", target)

        if target in self.config['active_objects']:
            self.log.debug("Enabling diverter since eject target is on the "
                           "active target list")
            self.enable()

        elif target in self.config['inactive_objects']:
            self.log.debug("Enabling diverter since eject target is on the "
                           "inactive target list")
            self.disable()

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
