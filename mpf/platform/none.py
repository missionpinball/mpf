"""Contains "dummy" code for a fake hardware platform. This doesn't do anything
really, rather, it's used for testing.

This is similar to the P-ROC's 'FakePinPROC' mode of operation, though unlike
that it doesn't require any P-ROC drivers to be installed.

This is good for first-time testing.

NOTE: At this point this is kind of a hack. Really it's the P-ROC platform
interface with all the functional stuff that actually talks to the P-ROC
pulled out.

Once we get the FAST drivers then we'll probably consolidate and rewrite these
for all three platforms. (P-ROC, FAST, and None) But until then, this should
work.

"""
# p_roc.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time
from mpf.system.hardware import (
    Platform, HardwareObject, HardwareDriver, HardwareSwitch,
    HardwareDirectLED)
from mpf.system.timing import Timing


class HardwarePlatform(object):

    def __init__(self, machine):
        self.log = logging.getLogger("'None' Platform")
        self.log.debug("Configuring machine for fake hardware.")
        self.machine = machine
        self.machine.hw_polling = True
        self.HZ = None
        self.secs_per_tick = None
        self.next_tick_time = None

        self.parent = Platform(self, machine)

    def process_hw_config(self):
        """Processes the hardware configuration when platform 'none' is used.

        At first it might seem weird to have this. Like, why do we have to
        process a hardware configuration if there's no hardware? The reason is
        even with no hardware, we need to read through the config files to
        create the software objects for the drivers, lights, and switches so
        they can be used by the python code. This is essentially all this
        module does.

        """

        pairs = [('Coils', self.machine.coils, DummyDriver),
                 ('Lamps', self.machine.lamps, DummyDriver),
                 ('Switches', self.machine.switches, DummySwitch),
                 ('LEDs', self.machine.leds, DummyLED)]

        for section, collection, klass in pairs:
            if section in self.machine.config:
                last_number = 0
                sect_dict = self.machine.config[section]
                for name in sect_dict:

                    item_dict = sect_dict[name]
                    item = None

                    # need a number, can be random
                    number = last_number
                    last_number += 1

                    item = klass(self, name, number)

                    if 'label' in item_dict:
                            item.parent.label = item_dict['label']

                    if 'type' in item_dict:
                        item.parent.type = item_dict['type']
                    if 'tags' in item_dict:
                        tags = item_dict['tags']
                        if type(tags) == str:
                            item.parent.tags = tags.split(',')
                        elif type(tags) == list:
                            item.parent.tags = tags
                        else:
                            self.log.warning('Configuration item named '
                                '"%s" has unexpected tags type %s. Should '
                                'be list or comma-delimited string.'
                                % (name, type(tags)))

                    if klass == DummySwitch:
                        if 'debounced' in item_dict and \
                             item_dict['debounced'] is False:
                            item.debounced = False
                    if klass == DummyDriver:
                        if ('pulseTime' in item_dict):
                            item.pulse_time = \
                                item_dict['pulseTime']
                        if 'polarity' in item_dict:
                            item.reconfigure(item_dict['polarity'])
                    if klass == DummyLED:
                        if ('polarity' in item_dict):
                            item.invert = not item_dict['polarity']

                    collection[name] = item.parent  # was 'item'
                    #item.parent.tags = collection[name].tags
                    self.log.debug("Creating fake hardware device: %s: "
                                     "%s:%s", section, name, number)

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is this
        premature optimization?)
        """
        self.next_tick_time = time.time()

    def hw_loop(self):

        if Timing.HZ:
            if self.next_tick_time <= time.time():
                self.machine.timer_tick()
                self.next_tick_time += Timing.secs_per_tick

    def set_hw_rule(self,
                    sw,
                    sw_activity,
                    coil_action_time,  # 0 = disable, -1 = hold forever
                    coil=None,
                    pulse_time=0,
                    pwm_on=0,
                    pwm_off=0,
                    delay=0,
                    recycle_time=0,
                    debounced=True,
                    drive_now=False):

        self.log.debug("Setting HW Rule. Switch:%s, Action ms:%s, Coil:%s, "
                   "Pulse:%s, pwm_on:%s, pwm_off:%s, Delay:%s, Recycle:%s,"
                   "Debounced:%s, Now:%s", sw.name, coil_action_time,
                   coil.name, pulse_time, pwm_on, pwm_off, delay,
                   recycle_time, debounced, drive_now)

    def clear_hw_rule(self, sw_num):
        for entry in self.hw_switch_rules.keys():  # slice for copy
            if entry.startswith(self.machine.switches.get_from_number(sw_num).name):
                del self.hw_switch_rules[entry]


class PlatformDriver(object):
    pass


class DummyHardwareObject(HardwareObject):
    """Base class for P-ROC Hardware Objects."""
    yaml_number = None

    def __init__(self, machine, name, number):
        super(DummyHardwareObject, self).__init__(machine, name, number)


class DummySwitch(object):
    """Represents a switch in a pinball machine connected to a P-ROC."""
    def __init__(self, machine, name, number):
        self.parent = HardwareSwitch(machine, name, number,
                                                  platform_driver=self)

    # todo add methods that query hardware-specific things of P-ROC switches,
    # if there are any??


class DummyLED(object):
    pass


class DummyDriver(PlatformDriver):

    def __init__(self, machine, name, number):
        self.log = logging.getLogger('DummyDriver')
        self.machine = machine
        self.number = number
        self.parent = HardwareDriver(machine, name, number, self)

    def disable(self):
        pass

    def pulse(self, milliseconds=None):
        pass

    def future_pulse(self, milliseconds=None, timestamp=0):
        pass

    def patter(self, on_time=10, off_time=10, original_on_time=0, now=True):
        pass

    def pulsed_patter(self, on_time=10, off_time=10, run_time=0, now=True):
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
