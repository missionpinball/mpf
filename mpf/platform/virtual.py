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

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.platform import Platform


class HardwarePlatform(Platform):
    """Base class for the virtual hardware platform."""

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring machine for virtual hardware.")
        self.machine.physical_hw = False

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the virtual hardware can and cannot do.
        self.features['max_pulse'] = 255
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False
        self.features['hw_enable_auto_disable'] = False

        # Make the platform features available to everyone
        self.machine.config['Platform'] = self.features
        # ----------------------------------------------------------------------

    def configure_driver(self, config, device_type='coil'):
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?
        return VirtualDriver(config['number']), config['number']

    def configure_switch(self, config):
        switch = VirtualSwitch(config['number'])
        # Return the switch object, the hardare number, and an integer of its
        # current state. (1 = active, 0 = inactive)

        state = 0

        if 'type' in config and config['type'] == 'NC':
            state = 1  # for NC switches, the default "inactive" state is 1.

        return switch, config['number'], state

    def configure_matrixlight(self, config):
        return VirtualMatrixLight(config['number']), config['number']

    def configure_led(self, config):
        return VirtualLED(config['number'])

    def configure_gi(self, config):
        return VirtualGI(config['number']), config['number']

    def configure_dmd(self):
        return VirtualDMD(self.machine)

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
                    self.machine.switches.number(sw_num).name):
                del self.hw_switch_rules[entry]


class VirtualSwitch(object):
    """Represents a switch in a pinball machine used with virtual hardware."""
    def __init__(self, number):
        self.log = logging.getLogger('VirtualSwitch')
        self.number = number


class VirtualMatrixLight(object):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualMatrixLight')
        self.number = number

    def on(self, brightness=255, fade_ms=0, start=0):
        pass

    def off(self):
        pass


class VirtualLED(object):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualLED')
        self.number = number

    def color(self, color, fade_ms=0, brightness_compensation=True):
        self.log.debug("Setting color: %s, fade: %s, comp: %s",
                       color, fade_ms, brightness_compensation)

    def disable(self):
        pass

    def enable(self, brightness_compensation=True):
        pass


class VirtualGI(object):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualGI')
        self.number = number

    def on(self, brightness, fade_ms, start):
        pass

    def off(self):
        pass


class VirtualDriver(object):

    def __init__(self, number):
        self.log = logging.getLogger('VirtualDriver')
        self.number = number

    def disable(self):
        pass

    def enable(self):
        pass

    def pulse(self, milliseconds=None):
        pass

    def future_pulse(self, milliseconds=None, timestamp=0):
        pass

    def pwm(self, on_ms=10, off_ms=10, original_on_ms=0, now=True):
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


class VirtualDMD(object):

    def __init__(self, machine):
        pass

    def update(self, pixel_array):
        pass

# The MIT License (MIT)

# Oringal code on which this module was based:
# Copyright (c) 2009-2011 Adam Preble and Gerry Stellenberg

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
