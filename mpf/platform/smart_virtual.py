"""Contains code for the smart_virtual platform."""
# smart_virtual.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

import time

from mpf.system.tasks import DelayManager
from mpf.system.utility_functions import Util
from mpf.platform.virtual import (HardwarePlatform as VirtualPlatform,
                                  VirtualDMD, VirtualDriver, VirtualGI,
                                  VirtualLED, VirtualMatrixLight,
                                  VirtualSwitch)


class HardwarePlatform(VirtualPlatform):
    """Base class for the smart_virtual hardware platform."""

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger("Smart Virtual Platform")
        self.log.debug("Configuring smart_virtual hardware interface.")

        self.delay = DelayManager()

    def __repr__(self):
        return '<Platform.SmartVirtual>'

    def initialize(self):
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize2)

    def _initialize2(self):
        for device in self.machine.ball_devices:
            if not device.is_playfield() and device.config['eject_coil']:
                device.config['eject_coil'].hw_driver.register_ball_switches(
                    device.config['ball_switches'])

                if device.config['eject_targets'][0] is not self.machine.playfield:
                    device.config['eject_coil'].hw_driver.set_target_device(device.config['eject_targets'][0])

    def configure_driver(self, config, device_type='coil'):
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        driver = SmartVirtualDriver(config['number'], self.machine, self)

        driver.driver_settings = config
        driver.driver_settings['pulse_ms'] = 30

        return driver, config['number']

    def write_hw_rule(self, *args, **kwargs):
        pass

    def clear_hw_rule(self, sw_name):
        sw_num = self.machine.switches[sw_name].number

        for entry in self.hw_switch_rules.keys():  # slice for copy
            if entry.startswith(
                    self.machine.switches.number(sw_num).name):
                del self.hw_switch_rules[entry]

    def tick(self):
        # ticks every hw loop (typically hundreds of times per sec)

        self.delay._process_delays(self.machine)

    def add_ball_to_device(self, device):
        if device.config['entrance_switch']:
            pass # todo

        found_switch = False

        if device.config['ball_switches']:
            for switch in device.config['ball_switches']:
                if self.machine.switch_controller.is_inactive(switch.name):
                    self.machine.switch_controller.process_switch(switch.name,
                                                                  1,
                                                                  True)
                    found_switch = True
                    break

            if not found_switch:
                raise AssertionError("KABOOM! We just added a ball to {} which"
                                     "was already full.".format(device.name))


class SmartVirtualDriver(VirtualDriver):

    def __init__(self, number, machine, platform):
        self.log = logging.getLogger('SmartVirtualDriver')
        self.number = number
        self.machine = machine
        self.platform = platform
        self.ball_switches = list()
        self.target_device = None

    def __repr__(self):
        return "SmartVirtualDriver.{}".format(self.number)

    def disable(self):
        pass

    def enable(self):
        pass

    def pulse(self, milliseconds=None):
        for switch in self.ball_switches:
            if self.machine.switch_controller.is_active(switch.name):
                self.machine.switch_controller.process_switch(switch.name, 0,
                                                              logical=True)
                break

        if self.target_device:
            self.platform.delay.add(ms=100,
                                    callback=self.platform.add_ball_to_device,
                                    device=self.target_device)

        if milliseconds:
            return milliseconds
        else:
            return self.driver_settings['pulse_ms']

    def register_ball_switches(self, switches):
        self.ball_switches.extend(switches)

    def set_target_device(self, target):
        self.target_device = target


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
