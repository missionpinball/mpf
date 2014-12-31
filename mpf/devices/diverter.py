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

        # configure defaults:
        if 'type' not in self.config:
            self.config['type'] = 'pulse'  # default to pulse to not fry coils
        if 'timeout' not in self.config:
            self.config['timeout'] = 0
        if 'auto_activate' not in self.config:
            self.config['auto_activate'] = True
        if 'activation_switch' not in self.config:
            self.config['activation_switch'] = None
        if 'activation_switch' not in self.config:
            self.config['activation_switch'] = None
        if 'disable_switch' not in self.config:
            self.config['disable_switch'] = None

        if 'target_when_active' not in self.config:
            self.config['target_when_active'] = None

        if 'target_when_inactive' not in self.config:
            self.config['target_when_inactive'] = None

        if self.config['auto_activate'] and (
                self.config['target_when_active'] or
                self.config['target_when_inactive']):
            self.enable_auto_activation()

        # convert the timeout to ms
        self.config['timeout'] = Timing.string_to_ms(self.config['timeout'])

        # register for events
        for event in self.config['enable_events']:
            self.machine.events.add_handler(event, self.enable)

        for event in self.config['disable_events']:
            self.machine.events.add_handler(event, self.disable)

    def enable(self, auto=False, **kwargs):
        """Enables this diverter.

        Args:
            auto: Boolean value which is used to indicate whether this
                diverter enabled itself automatically. This is passed to the
                event which is posted.

        If an 'activation_switch' is configured, then this method writes a
        hardware autofire rule to the pinball controller which fires the
        diverter coil when the switch is activated.

        If no `activation_switch` is specified, then the diverter is activated
        immediately.
        """

        self.machine.events.post('diverter_' + self.name + '_enabling',
                                 auto=auto)

        if self.config['activation_switch']:
            self.enable_hw_switch()
        else:
            self.activate()

        if self.config['disable_switch']:
            self.machine.switch_controller.add_switch_handler(
                self.config['disable_switch'],
                self.disable)

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

        self.machine.events.post('diverter_' + self.name + '_disabling',
                                 auto=auto)

        self.log.debug("Disabling Diverter")
        if self.config['activation_switch']:
            self.disable_hw_switch()
        else:
            self.deactivate()

    def activate(self):
        """Physically activates this diverter's coil."""

        self.log.debug("Activating Diverter")
        self.machine.events.post('diverter_' + self.name + '_activating')
        if self.config['type'] == 'pulse':
            self.machine.coils[self.config['coil']].pulse()
        elif self.config['type'] == 'hold':
            self.machine.coils[self.config['coil']].enable()
            self.schedule_disable()

    def deactivate(self):
        """Physically deactivates this diverter's coil."""
        self.log.debug("Deactivating Diverter")
        self.machine.events.post('diverter_' + self.name + '_deactivating')
        self.machine.coils[self.config['coil']].disable()

    def enable_auto_activation(self):
        """Enables the auto-activation of this diverter, which means it will
        enable and disable itself based on the state of its target devices.
        """

        self.config['auto_activate'] = True

        if self.config['target_when_active'] == 'ball_device':
            self.machine.events.add_handler('balldevice_' +
                                            self.config['target_when_active'] +
                                            '_ball_request', self.enable,
                                            auto=True)
            self.machine.events.add_handler('balldevice_' +
                                            self.config['target_when_active'] +
                                            '_cancel_ball_request',
                                            self.disable, auto=True)
        elif self.config['target_when_active'] == 'diverter':
            self.machine.events.add_handler('diverter_' +
                                            self.config['target_when_active'] +
                                            '_enabling', self.enable, auto=True)
            self.machine.events.add_handler('diverter_' +
                                            self.config['target_when_active'] +
                                            '_disabling',
                                            self.enable, auto=True)

        if self.config['target_when_inactive'] == 'ball_device':
            self.machine.events.add_handler('balldevice_' +
                                            self.config['target_when_inactive']
                                            + '_ball_request', self.disable,
                                            auto=True)
            self.machine.events.add_handler('balldevice_' +
                                            self.config['target_when_inactive']
                                            + '_cancel_ball_request',
                                            self.enable, auto=True)
        elif self.config['target_when_inactive'] == 'diverter':
            self.machine.events.add_handler('diverter_' +
                                            self.config['target_when_active'] +
                                            '_enabling', self.disable,
                                            auto=True)
            self.machine.events.add_handler('diverter_' +
                                            self.config['target_when_active'] +
                                            '_disabling',
                                            self.disable, auto=True)


    def disable_auto_activation(self):
        """Disables the auto-activation of this diverter"""

    def schedule_disable(self, time=None):
        """Schedules a delay to deactivate this diverter.

        Args:
            time: The MPF string time of how long you'd like the delay before
            deactivating the diverter. Default is None which means it uses the
            'timeout' setting configured for this diverter. If there is no
            'timeout' setting and no delay is passed, it will disable the
            diverter immediately.
        """

        if time is not None:
            delay = Timing.string_to_ms(time)

        elif self.config['timeout']:
            delay = self.config['timeout']

        if delay:
            self.delay.add('disable_held_coil', delay, self.disable_held_coil)
        else:
            self.disable_held_coil()

    def enable_hw_switch(self):
        """Enables the hardware switch rule which causes this diverter to
        activate when the switch is hit.

        This is typically used for diverters on loops and ramps where you don't
        want the diverter to phsyically activate until the ramp entry switch is
        activated.

        If this diverter is configured with a timeout, this method will also
        set switch handlers which will set a delay to deactivate the diverter
        once the activation timeout expires.

        If this diverter is configured with a deactivation switch, this method
        will set up the switch handlers to deactivate the diverter when the
        deactivation switch is activated.
        """
        self.log.debug("Enabling Diverter for hw switch: %s",
                       self.config['activation_switch'])

        if self.config['type'] == 'hold':

            self.machine.platform.set_hw_rule(
                sw_name=self.config['activation_switch'],
                sw_activity='active',
                coil_name=self.config['coil'],
                coil_action_ms=-1,
                pulse_ms=self.machine.coils[self.config['coil']].config['pulse_ms'],
                pwm_on=self.machine.coils[self.config['coil']].config['pwm_on'],
                pwm_off=self.machine.coils[self.config['coil']].config['pwm_off'],
                debounced=False)

            # If there's a timeout then we need to watch for the hw switch to
            # be activated so we can disable the diverter

            if self.config['timeout']:
                self.machine.switch_controller.add_switch_handler(
                    self.config['activation_switch'],
                    self.schedule_disable)

        elif self.config['type'] == 'pulse':

            self.machine.platform.set_hw_rule(
                sw_name=self.config['activation_switch'],
                sw_activity='active',
                coil_name=self.config['coil'],
                coil_action_ms=1,
                pulse_ms=self.machine.coils[self.config['main_coil']].config['pulse_ms'],
                debounced=False)

    def disable_hw_switch(self):
        """Removes the hardware rule to disable the hardware activation switch
        for this diverter.
        """
        self.machine.platform.clear_hw_rule(self.config['activation_switch'])

    def disable_held_coil(self):
        """Physically disables the coil holding this diverter open."""
        self.machine.coils[self.config['coil']].disable()


# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
