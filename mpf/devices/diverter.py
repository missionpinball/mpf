""" Parent contains the base class for diverter devices."""
# diverter.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing


class Diverter(Device):
    """Represents a diverter in a pinball machine."""

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
        if 'activation_switch' not in self.config:
            self.config['activation_switch'] = None
        if 'enable_events' not in self.config:
            self.config['enable_events'] = None
        else:
            self.config['enable_events'] = self.machine.string_to_list(
                                                self.config['enable_events'])
        if 'disable_events' not in self.config:
            self.config['disable_events'] = None
        else:
            self.config['disable_events'] = self.machine.string_to_list(
                                                self.config['disable_events'])
        if 'disable_switch' not in self.config:
            self.config['disable_switch'] = None
        if 'target_when_enabled' not in self.config:
            self.config['target_when_enabled'] = None  # todo
        if 'target_when_disabled' not in self.config:
            self.config['target_when_disabled'] = None  # todo

        # convert the timeout to ms
        self.config['timeout'] = Timing.string_to_ms(self.config['timeout'])

        # register for events
        for event in self.config['enable_events']:
            self.machine.events.add_handler(event, self.enable)

        for event in self.config['disable_events']:
            self.machine.events.add_handler(event, self.disable)

    def enable(self):
        """Enables this diverter.

        If an 'activation_switch' is configured, then this method writes a hardware
        autofire rule to the pinball controller which fires the diverter coil
        when the switch is activated.

        If no `activation_switch` is specified, then the diverter is activated
        immediately.
        """

        if self.config['activation_switch']:
            self.enable_hw_switch()
        else:
            self.activate()

        if self.config['disable_switch']:
            self.machine.switch_controller.add_switch_handler(
                self.config['disable_switch'],
                self.disable)

    def disable(self, deactivate=True, **kwargs):
        """Disables this diverter.

        This method will remove the hardware rule if this diverter is activated
        via a hardware switch.

        Args:
            deactivate: A boolean value which specifies whether this diverter
                should be immediately deactived.
            **kwargs: This is here because this disable method is called by
                whatever event the game programmer specifies in their machine
                configuration file, so we don't know what event that might be
                or whether it has random kwargs attached to it.
        """
        self.log.debug("Disabling Diverter")
        if self.config['activation_switch']:
            self.disable_hw_switch()
        if deactivate:
            self.deactivate()

    def activate(self):
        """Physically activates this diverter."""

        self.log.debug("Activating Diverter")
        self.machine.events.post('diverter_' + self.name + '_activating')
        if self.config['type'] == 'pulse':
            self.machine.coils[self.config['coil']].pulse()
        elif self.config['type'] == 'hold':
            self.machine.coils[self.config['coil']].enable()
            self.schedule_disable()

    def deactivate(self):
        """Physically deactivates this diverter."""
        self.log.debug("Deactivating Diverter")
        self.machine.coils[self.config['coil']].disable()

    def schedule_disable(self):
        """Schedules a delay to deactivate this diverter based on the configured
        timeout.
        """
        if self.config['timeout']:
            self.delay.add('disable_held_coil',
                           self.config['timeout'],
                           self.disable_held_coil)

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
