""" Contains the base class for autofire coil devices."""
# autofire.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.device import Device


class AutofireCoil(Device):
    """Base class for coils in the pinball machine which should fire
    automatically based on switch activity using hardware switch rules.

    autofire_coils are used when you want the coils to respond "instantly"
    without waiting for the lag of the python game code running on the host
    computer.

    Examples of autofire_coils are pop bumpers, slingshots, and flippers.

    Args: Same as Device.
    """

    config_section = 'autofire_coils'
    collection = 'autofires'
    class_label = 'autofire'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(AutofireCoil, self).__init__(machine, name, config, collection,
                                           validate=validate)

        self.switch_activity = 1

        self.coil = self.config['coil']
        self.switch = self.config['switch']

        if self.config['reverse_switch']:
            self.switch_activity = 0

        self.validate()

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

    def validate(self):
        """Autofire rules only work if the switch is on the same platform as the
        coil.

        In the future we may expand this to support other rules various platform
        vendors might have.

        """

        if self.switch.platform == self.coil.platform:
            self.platform = self.coil.platform
            return True
        else:
            return False

    def enable(self, **kwargs):
        """Enables the autofire coil rule."""

        # todo disable first to clear any old rules?

        self.log.debug("Enabling")

        if self.config['pulse_ms'] is None:
            self.config['pulse_ms'] = self.coil.config['pulse_ms']

        if self.config['pwm_on_ms'] is None:
            self.pwm_on_ms = self.coil.config['pwm_on']

        if self.config['pwm_off_ms'] is None:
            self.config['pwm_on_ms'] = self.coil.config['pwm_off']

        if self.config['coil_action_ms'] is None:
            self.config['coil_action_ms'] = self.config['pulse_ms']

        self.platform.set_hw_rule(sw_name=self.switch.name,
                                  sw_activity=self.switch_activity,
                                  coil_name=self.coil.name,
                                  coil_action_ms=self.config['coil_action_ms'],
                                  pulse_ms=self.config['pulse_ms'],
                                  pwm1=self.config['pwm_on_ms'],
                                  pwm_off=self.config['pwm_off_ms'],
                                  delay=self.config['delay'],
                                  recycle_time=self.config['recycle_ms'],
                                  debounced=self.config['debounced'],
                                  drive_now=self.config['drive_now'])

    def disable(self, **kwargs):
        """Disables the autofire coil rule."""
        self.log.debug("Disabling")
        self.platform.clear_hw_rule(self.switch.name)

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
