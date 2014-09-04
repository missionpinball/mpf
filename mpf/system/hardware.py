""" Contains the parent classes Platform, Device, and DeviceCollection
"""
# hardware.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time
from collections import defaultdict


class Platform(object):
    """ Parent class for the machine's hardware controller.

    This is the class that each hardware controller (such as P-ROC or FAST)
    will subclass to talk to their hardware. If there is no physical hardware
    attached, then this class can be used on its own. (Many of the methods
    will do nothing and your game will work.)

    For example, the P-ROC HardwarePlatform class will have a Driver class
    with methods such as pulse() to fire a coil.

    """
    def __init__(self, machine):
        self.machine = machine
        self.HZ = None
        self.secs_per_tick = None
        self.next_tick_time = None
        self.features = {}
        self.hw_switch_rules = {}

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['max_pulse'] = 255
        self.features['hw_polling'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is
        this premature optimization?)

        """
        self.next_tick_time = time.time()

    def set_hw_rule(self,
                    sw_name,  # switch name
                    sw_activity,  # active or inactive?
                    coil_name=None,  # coil name
                    coil_action_ms=0,  # total time coil is active for
                    pulse_ms=0,  # ms to pulse the coil?
                    pwm_on=0,  # 'on' ms of a pwm-based patter
                    pwm_off=0,  # 'off' ms of a pwm-based patter
                    delay=0,  # delay before firing?
                    recycle_time=0,  # wait before firing again?
                    debounced=False,  # should coil wait for debounce?
                    drive_now=False,  # should rule check sw and fire coil now?
                    ):
        """Writes the hardware rule to the controller.

        """

        self.log.debug("Writing HW Rule to controller")

        sw = self.machine.switches[sw_name]  # todo make a nice error
        coil = self.machine.coils[coil_name]  # here too

        # convert sw_activity to hardware. (The game framework uses the terms
        # 'active' and 'inactive,' which take into consideration whether a
        # switch is normally open or normally closed. For example if we want to
        # fire a coil when a switch that is normally closed is activated, the
        # actual hw_rule we setup has to be when that switch opens, not closes.

        if sw_activity == 'active':
            sw_activity = 1
        elif sw_activity == 'inactive':
            sw_activity = 0
        else:
            raise ValueError('Invalid "switch activity" option for '
                             'AutofireCoil: %s. Valid options are "active"'
                             ' or "inactive".' % (sw_name))
        if self.machine.switches[sw_name].type == 'NC':
            sw_activity = sw_activity ^ 1  # bitwise invert

        self._do_set_hw_rule(sw, sw_activity, coil_action_ms, coil,
                            pulse_ms, pwm_on, pwm_off, delay, recycle_time,
                            debounced, drive_now)

    def clear_hw_rule(self, sw_name):
        """ Clears all the hardware switch rules for a switch, meaning those
        switch actions will no longer affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers or bumpers during tilt, game
        over, etc.

        """
        self._do_clear_hw_rule(self.machine.switches[sw_name].number)


class Device(object):
    """ Generic parent class of for every hardware object in a pinball machine.

    """
    def __init__(self, machine, name, config=None, collection=-1):
        self.log.debug("Creating device")
        self.machine = machine
        self.name = name
        self.tags = []
        self.label = None
        self.config = defaultdict(lambda: None, config)

        if config:
            self.config.update(config)

            if 'tags' in config:
                self.tags = self.machine.string_to_list(config['tags'])
            if 'label' in config:
                self.label = config['label']  # todo change to multi lang
            # todo more pythonic way, like self.label = blah if blah?

        # Add this instance to our dictionary for this type of device
        if collection != -1:
            # Have to use -1 here instead of None to catch an empty collection
            collection[name] = self

        #self.configure(config)

    def configure(self, config):
        """ Each device subclass should implement their own configure() method
        which will be called to set up and configure the device.

        """
        pass


class DeviceCollection(dict):
    """A collection of Devices.

    One instance of this class will be created for each different type of
    hardware device (such as coils, lights, switches, ball devices, etc.)

    """

    def __getattr__(self, attr):
        # We use this to allow the programmer to access a hardware item like
        # self.coils.coilname
        try:
            # If we were passed a name of an item
            if type(attr) == str:
                return self[attr]
            elif type(attr) == int:
                self.get_from_number(number=attr)
        except KeyError:
            raise KeyError('Error: No hardware device defined for:', attr)

        # todo there's something that's not working here that I need to figure
        # out. An example like this will fail:
        # self.hold_coil = self.machine.coils[config['hold_coil']]
        # even if config is a defaultdict, because config will return
        # None, and we can't call this DeviceCollection on None. Maybe make
        # default dict return some non-None as its default which we can catch
        # here?

    def __iter__(self):
        for item in self.itervalues():
            yield item

    def items_tagged(self, tag):
        output = []
        for item in self:
            if tag in item.tags:
                output.append(item)
        return output

    def get_from_number(self, number):
        """ Returns an item name based on its number.
        """
        for name, obj in self.iteritems():
            if obj.number == number:
                return self[name]


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
