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
from mpf.system.config import Config


class HardwarePlatform(Platform):
    """Base class for the virtual hardware platform."""

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring virtual hardware interface.")
        #self.machine.physical_hw = False

        # Since the virtual platform doesn't have real hardware, we need to
        # maintain an internal list of switches that were confirmed so we have
        # something to send when MPF needs to know the hardware states of
        # switches
        self.hw_switches = dict()
        self.initial_states_sent = False

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the virtual hardware can and cannot do.
        self.features['max_pulse'] = 255
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False

        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

    def __repr__(self):
        return '<Platform.Virtual>'

    def configure_driver(self, config, device_type='coil'):
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        driver = VirtualDriver(config['number'])

        driver.driver_settings = config
        driver.driver_settings['pulse_ms'] = 30

        return driver, config['number']

    def configure_switch(self, config):
        # We want to have the virtual platform set all the initial switch states
        # to inactive, so we have to check the config.

        state = 0

        if config['type'].upper() == 'NC':
            state = 1

        self.hw_switches[config['number']] = state

        switch = VirtualSwitch(config['number'])

        switch.driver_settings = config

        return switch, config['number']

    def get_hw_switch_states(self):

        if not self.initial_states_sent:

            if 'virtual_platform_start_active_switches' in self.machine.config:

                initial_active_switches = [self.machine.switches[x].number for x in
                    Config.string_to_list(
                        self.machine.config['virtual_platform_start_active_switches'])]

                for k, v in self.hw_switches.iteritems():
                    if k in initial_active_switches:
                        self.hw_switches[k] ^= 1

            self.initial_states_sent = True

        else:
            switches = [x for x in self.machine.switches if x.platform == self]

            for switch in switches:
                self.hw_switches[switch.number] = switch.state ^ switch.invert

        return self.hw_switches

    def configure_matrixlight(self, config):
        return VirtualMatrixLight(config['number']), config['number']

    def configure_led(self, config):
        return VirtualLED(config['number'])

    def configure_gi(self, config):
        return VirtualGI(config['number']), config['number']

    def configure_dmd(self):
        return VirtualDMD(self.machine)

    def write_hw_rule(self, *args, **kwargs):
        pass

    def clear_hw_rule(self, sw_name):
        sw_num = self.machine.switches[sw_name].number

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
        #self.log.debug("Setting color: %s, fade: %s, comp: %s",
        #               color, fade_ms, brightness_compensation)
        pass

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

    def __repr__(self):
        return "VirtualDriver.{}".format(self.number)

    def validate_driver_settings(self, **kwargs):
        return dict()

    def disable(self):
        pass

    def enable(self):
        pass

    def pulse(self, milliseconds=None):
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

    def update(self, data):
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
