"""Contains code for a virtual hardware platform. At this point this is more
for testing before you have a P-ROC or FAST board installed. Eventually this
can be used to allow the MPF to drive PinMAME and Virtual Pinball machines.

This is similar to the P-ROC's 'FakePinPROC' mode of operation, though unlike
that it doesn't require any P-ROC drivers or modules to be installed.

"""
# virtual.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time
from mpf.system.timing import Timing
from mpf.system.hardware import Platform


class HardwarePlatform(Platform):
    """Base class for the virtual hardware platform. This is a subclass of
    mpf.system.hardware.Platform.

    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring machine for virtual hardware.")

        # Set the 'None Hardware' specific platform features
        self.features['max_pulse'] = 255
        self.features['hw_polling'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False

    def configure_driver(self, config):
        """ Configures a virtual driver (coil, flasher, etc.).

        Parameters
        ----------

        config : dict

        Returns
        -------

        object
            Returns a link to the newly-created VirtualDriver object.

        """
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        return VirtualDriver(config['number'])

    def configure_switch(self, config):
        """ Configures a virtual switch.

        Parameters
        ----------

        config : str

        number : str
            The number of the driver.

        debounce : bool
            `debounce` is ignored on this virtual platform, but it's included
            as a parameter for compatibility with code written for other
            platforms.

        Returns
        -------

        switch : object
            A reference to the switch object that was just created.

        number : int
            The number of the driver. This is the same as whatever you passed
            as an initial parameter.

        state : int
            The current hardware state of the switch, used to set the initial
            state state in the machine. A value of 0 means the switch is open,
            and 1 means it's closed. Note this state is the physical state of
            the switch, so if you configure the switch to be normally-closed
            (i.e. "inverted" then your code will have to invert it too.) MPF
            handles this automatically if the switch type is 'NC'.

        """
        switch = VirtualSwitch(config['number'])

        # Return the switch object, the hardare number, and an integer of its
        # current state. (1 = active, 0 = inactive)
        return switch, config['number'], 0

    def _do_set_hw_rule(self,
                    sw,
                    sw_activity,
                    coil_action_ms,  # 0 = disable, -1 = hold forever
                    coil=None,
                    pulse_ms=0,
                    pwm_on=0,
                    pwm_off=0,
                    delay=0,
                    recycle_time=0,
                    debounced=True,
                    drive_now=False):

        pass
        # todo create switch handlers to fire coils based on these hardware
        # rules

    def _do_clear_hw_rule(self, sw_num):
        for entry in self.hw_switch_rules.keys():  # slice for copy
            if entry.startswith(
                    self.machine.switches.get_from_number(sw_num).name):
                del self.hw_switch_rules[entry]


class VirtualSwitch(object):
    """Represents a switch in a pinball machine used with virtual hardware."""
    def __init__(self, number):
        self.log = logging.getLogger('VirtualSwitch')
        self.number = number


class VirtualLED(object):
    pass


class VirtualDriver(object):

    def __init__(self, number):
        self.log = logging.getLogger('VirtualDriver')
        self.number = number

    def disable(self):
        pass

    def pulse(self, milliseconds=None):
        pass

    def future_pulse(self, milliseconds=None, timestamp=0):
        pass

    def patter(self, on_ms=10, off_ms=10, original_on_ms=0, now=True):
        pass

    def pulsed_patter(self, on_ms=10, off_ms=10, run_time=0, now=True):
        pass

    def schedule(self, schedule, cycle_seconds=0, now=True):
        pass

    def state(self):
        pass

    def tick(self):
        pass

    def reconfigure(self, polarity):
        pass

# The MIT License (MIT)

# Oringal code on which this module was based:
# Copyright (c) 2009-2011 Adam Preble and Gerry Stellenberg

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
