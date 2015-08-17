""" Contains the base class for autofire coil devices."""
# autofire.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
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

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('AutofireCoil.' + name)

        super(AutofireCoil, self).__init__(machine, name, config, collection)

        self.platform = None

        # todo convert to dict
        self.switch = None
        self.switch_activity = 'active'
        self.coil = None
        self.coil_action_ms = 0  # -1 for hold, 0 for disable, 1+ for pulse
        self.pulse_ms = 0
        self.pwm_on_ms = 0
        self.pwm_off_ms = 0
        self.delay = 0
        self.recycle_ms = 125
        self.debounced = False
        self.drive_now = False

        self.configure()

        self.validate()

    def configure(self, config=None):
        """Configures an autofire coil.

        Args:
            config : A dictionary which contains all the settings this
            coil should be configured with.
        """

        # Merge in any new changes that were just passed
        if config:
            self.config.update(self.machine.config_processor.process_config2(
            'device:' + self.class_label, config, self.name))

        # Required
        self.coil = self.config['coil']
        self.switch = self.config['switch']

        # Don't want to use defaultdict here because a lot of the config dict
        # items might have 0 as a legit value, so it makes 'if item:' not work

        # Translate 'active' / 'inactive' to hardware open (0) or closed (1)
        if self.config['reverse_switch']:
            self.switch_activity = 0

        if self.config['pulse_ms'] is None:
            self.pulse_ms = self.config['coil'].config['pulse_ms']

        if self.config['pwm_on_ms'] is None:
            self.pwm_on_ms = self.config['coil'].config['pwm_on']

        if self.config['pwm_off_ms'] is None:
            self.pwm_on_ms = self.config['coil'].config['pwm_off']

        if self.config['coil_action_ms']:
            self.coil_action_ms = self.config['coil_action_ms']
        else:
            self.coil_action_ms = self.pulse_ms

        self.delay = self.config['delay']
        self.recycle_ms = self.config['recycle_ms']
        self.debounced = self.config['debounced']
        self.drive_now = self.config['drive_now']

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
        if not self.coil:
            self.configure()

        self.platform.set_hw_rule(sw_name=self.switch.name,
                                  sw_activity=self.switch_activity,
                                  coil_name=self.coil.name,
                                  coil_action_ms=self.coil_action_ms,
                                  pulse_ms=self.pulse_ms,
                                  pwm_on=self.pwm_on_ms,
                                  pwm_off=self.pwm_off_ms,
                                  delay=self.delay,
                                  recycle_time=self.recycle_ms,
                                  debounced=self.debounced,
                                  drive_now=self.drive_now)

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
