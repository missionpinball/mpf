""" Contains the class for hardware objects, as well as generic subclasses for
each type of hardware item (LED, Lamp, Coil, Switch, Stepper). Then each
platform will subclass these to add the platform-specific things it needs.
"""
# hardware.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time
from mpf.system.timing import Timing
import uuid


class Platform(object):
    """Base class which communicates with the actual platform drivers."""
    def __init__(self, platform_object, machine):
        self.log = logging.getLogger('Platform')
        self.hw_platform = platform_object
        self.machine = machine

    def process_hw_config(self):
        self.hw_platform.process_hw_config()

    def timer_config(self, HZ):
        if HZ:
            Timing.HZ = HZ
            Timing.secs_per_tick = 1 / float(HZ)

    def timer_initialize(self):
        self.hw_platform.timer_initialize()

    def hw_loop(self):
        self.hw_platform.hw_loop()

    def set_hw_rule(self,
                    sw_name,  # switch name
                    sw_activity,  # active or inactive?
                    coil_name=None,  # coil name
                    coil_action_time=0,
                    pulse_time=0,  # ms to pulse the coil?
                    pwm_on=0,
                    pwm_off=0,
                    delay=0,  # delay before firing?
                    recycle_time=0,
                    debounced=False,
                    drive_now=False):  # wait before firing again?

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

        self.hw_platform.set_hw_rule(sw,
                                     sw_activity,
                                     coil_action_time,
                                     coil,
                                     pulse_time,
                                     pwm_on,
                                     pwm_off,
                                     delay,
                                     recycle_time,
                                     debounced,
                                     drive_now)

    def clear_hw_rule(self, sw_name):
        """ Clears all the hardware switch rules for a switch, meaning those
        switch actions will no longer affect coils.
        """
        self.hw_platform.clear_hw_rule(self.machine.switches[sw_name].number)


class HardwareObject(object):
    def __init__(self, machine, name, number=-1):
        self.machine = machine
        self.name = name
        self.tags = []
        self.label = None
        self.time_last_changed = 0

        if number == -1:
            self.number = uuid.uuid4().int
            # some hw doesn't have a number, but we need it for everything
            # else to work, so we just make one up. Maybe this should change to
            # not require a number?
        else:
            self.number = number


class HardwareDriver(HardwareObject):
    """Generic class that holds driver elements.

    This exposes the methods you can use. Then each platform module subclasses
    these to actually perform the actions.
    """

    log = logging.getLogger("HardwareDriver")
    platform_driver = None

    def __init__(self, machine, name, number, platform_driver):
        super(HardwareDriver, self).__init__(machine, name, number)
        self.platform_driver = platform_driver
        self.pulse_time = 30
        self.pwm_on_time = 0
        self.pwm_off_time = 0

    def disable(self):
        """ Disables this driver """
        self.log.debug("Disabling Driver: %s", self.name)
        self.time_last_changed = time.time()
        # todo also disable the timer which reenables this

    def pulse(self, milliseconds=None):
        """ Enables this driver. If no params are provided then it uses the
        default. """
        if milliseconds is None:
            milliseconds = self.pulse_time
        # todo also disable the timer which reenables this
        self.log.debug("Pulsing Driver %s for %dms", self.name, milliseconds)
        self.platform_driver.pulse(milliseconds)
        self.time_last_changed = time.time()

    def pwm(self, on_time, off_time, orig_on_time):
        pass  # todo
        self.time_last_changed = time.time()
        # todo also disable the timer which reenables this

    def pulse_pwm(self):
        pass  # todo
        self.time_last_changed = time.time()
        # todo also disable the timer which reenables this

    def enable(self):
        pass  # todo
        # get the secs per tick
        # set a pulse for 2.5x secs per tick
        # set a timer that runs each tick to re-up it
        self.time_last_changed = time.time()


class HardwareDict(dict):
    """A collection of HardwareObjects that make up all the hardware of one type.
    For example, there will be subclasses of this for LEDs, Lamps, Switches,
    Coils, etc.
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


class HardwareSwitch(HardwareObject):
    def __init__(self, machine, name, number, platform_driver, type='NO'):
        super(HardwareSwitch, self).__init__(machine, name, number)
        self.log = logging.getLogger("HardwareSwitch")
        self.type = type  # NC or NO
        self.state = False
        self.last_changed = None
        self.hw_timestamp = None
        self.debounced = True
        self.platform_driver = platform_driver

    def _set_state(self, state):
        self.state = state

    def _is_state(self, state, seconds=None):
        if self.state == state:
            if seconds is not None:
                return self._time_since_change() > seconds
            else:
                return True
        else:
            return False

    def _is_active(self, seconds=None):
        if self.type == 'NO':
            return self._is_state(state=True, seconds=seconds)
        else:
            return self._is_state(state=False, seconds=seconds)

    def _is_inactive(self, seconds=None):
        if self.type == 'NC':
            return self._is_state(state=True, seconds=seconds)
        else:
            return self._is_state(state=False, seconds=seconds)

    def _time_since_change(self):
        if self._last_changed is None:
            return 1000000
        else:
            return time.time() - self._last_changed

    def _reset_timer(self):

        self._last_changed = time.time()

    def _state_str(self):
        if self._is_closed():
            return 'closed'
        else:
            return 'open  '


class HardwareLight(HardwareObject):
    """ Parent class of "lights" in a pinball machine. These can either be
    traditional incandescent lamps (or replacement LEDs) connected to a lamp
    matrix, or they can be LEDs connected to an LED control board.
    """
    def __init__(self):
        self.log = logging.getLogger('HardwareMatrixLight')


class HardwareMatrixLight(HardwareLight):
    """ Represents a light connected to a traditional lamp matrix. Could
    technically be an incandescent lamp or a replacement single-color LED.

    Note you cannot control brightness on these. They're either "on" or "off."

    Also you can't control the color. (Color is dictated by the color of the
    light and/or the color of the plastic insert or cap.)
    """

    def __init__(self):
        self.log = logging.getLogger('HardwareMatrixLight')

    def enable(self):
        pass

    def disable(self):
        pass


class HardwareDirectLED(HardwareLight):
    """ Represents an LED connected to an LED interface board. Can have any
    number of elements. Typically it's single element (single color), or three
    element (RGB). (Though dual element red/green also exist.)
    """
    def __init__(self, machine, name, number, platform_driver):
        HardwareObject.__init__(self, machine, name, number)
        self.log = logging.getLogger('HardwareDirectLED')
        self.platform_driver = platform_driver

        self.num_elements = None

        self.brightness_compensation = [1.0, 1.0, 1.0]
        # brightness_compensation allows you to set a default multiplier for
        # the "max" brightness of an LED. Recommended setting is 0.85
        self.default_fade = 0

        self.current_color = []  # one item for each element, 0-255

    def color(self, color):
        """ Set an LED to a color. Color is a dictionary of ints, one for R, G,
        and B. Single or dual color LEDs only use the first or first two
        entries
        """

        # If this LED has a default fade set, use color_with_fade instead:
        if self.default_fade:
            self.fade(color, self.default_fade)
            return

    def fade(self, color, fadetime):
        """ Fades the LED to the color via the fadetime in ms """
        pass

    def disable(self):
        """ Disables an LED, including all elements of a multi-color LED.
        """
        pass

    def enable(self):
        """ Enables all the elements of an LED. Really only useful for single
        color LEDs.
        """
        pass

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
