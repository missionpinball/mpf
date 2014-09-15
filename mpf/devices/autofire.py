""" Contains the base class for autofire coil devices."""
# autofire.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.devices import Device


class AutofireCoil(Device):
    """Base class for coils in the pinball machine which should fire
    automatically based on switch activity using hardware switch rules.

    Autofire coils are used when you want the coils to respond "instantly"
    without waiting for the lag of the python game code running on the host
    computer.

    Examples of Autofire Coils are pop bumpers, slingshots, and flippers.

    """

    config_section = 'Autofire Coils'
    collection = 'autofires'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('AutofireCoil.' + name)
        super(AutofireCoil, self).__init__(machine, name, config, collection)

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

        if config:
            self.configure(config)

    def configure(self, config=None):
        """Configures an autofire coil.

        Parameters
        ----------

        config : dictionary
            The configuration dictionary which contains all the settings this
            coil should be configured with.

        """
        if not config:
            self.log.error("No configuration received for AutofireCoil: %s",
                           self.name)

        # Required
        self.coil = config['coil']
        self.switch = config['switch']

        # Don't want to use defaultdict here because a lot of the config dict
        # items might have 0 as a legit value, so it makes 'if item:' not work

        # Translate 'active' / 'inactive' to hardware open (0) or closed (1)
        if 'switch activity' in config:
            self.switch_activity = config['switch_activity']

        if 'pulse_ms' in config:
            self.pulse_ms = config['pulse_ms']
        else:
            self.pulse_ms = self.machine.coils[config['coil']].config['pulse_ms']

        if 'pwm_on_ms' in config:
            self.pwm_on_ms = config['pwm_on_ms']
        else:
            self.pwm_on_ms = self.machine.coils[config['coil']].config['pwm_on']

        if 'pwm_off_ms' in config:
            self.pwm_off_ms = config['pwm_off_ms']
        else:
            self.pwm_off_ms = self.machine.coils[config['coil']].config['pwm_off']

        if 'coil_action_ms' in config:
            self.coil_action_ms = config['coil_action_ms']
        else:
            self.coil_action_ms = self.pulse_ms

        if 'delay' in config:
            self.delay = config['delay']

        if 'recycle_ms' in config:
            self.recycle_ms = config['recycle_ms']

        if 'debounced' in config:
            self.debounced = config['debounced']

        if 'drive_now' in config:
            self.drive_now = config['drive_now']

    def enable(self):
        """Enables the autofire coil rule."""
        if not self.coil:
            self.configure()

        self.machine.platform.set_hw_rule(sw_name=self.switch,
                                       sw_activity=self.switch_activity,
                                       coil_name=self.coil,
                                       coil_action_ms=self.coil_action_ms,
                                       pulse_ms=self.pulse_ms,
                                       pwm_on=self.pwm_on_ms,
                                       pwm_off=self.pwm_off_ms,
                                       delay=self.delay,
                                       recycle_time=self.recycle_ms,
                                       debounced=self.debounced,
                                       drive_now=self.drive_now)

    def disable(self):
        """Disables the autofire coil rule."""
        self.machine.platform.clear_hw_rule(self.switch)

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