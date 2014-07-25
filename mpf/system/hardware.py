""" Contains the parent class for hardware objects, as well as generic subclasses for
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
                    coil_action_time=0,  # total time coil is active for
                    pulse_time=0,  # ms to pulse the coil?
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

        self._do_set_hw_rule(sw, sw_activity, coil_action_time, coil,
                            pulse_time, pwm_on, pwm_off, delay, recycle_time,
                            debounced, drive_now)

    def clear_hw_rule(self, sw_name):
        """ Clears all the hardware switch rules for a switch, meaning those
        switch actions will no longer affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers or bumpers during tilt, game
        over, etc.

        """
        self._do_clear_hw_rule(self.machine.switches[sw_name].number)

    def _do_set_hw_rule(self, *args, **kwargs):
        pass

    def _do_clear_hw_rule(self, *args, **kwargs):
        pass


class HardwareObject(object):
    """ Generic parent class of for every hardware object in a pinball machine.

    """
    def __init__(self, machine, name, config, collection=-1):
        self.machine = machine
        self.name = name
        self.config = config
        self.tags = []
        self.label = None
        self.time_last_changed = 0

        # todo dunno if we want to keep number here in this parent class?
        if config['number']:
            self.number = config['number']
        else:
            self.number = uuid.uuid4().int
            # some hw doesn't have a number, but we need it for everything
            # else to work, so we just make one up. Maybe this should change to
            # not require a number?

        if 'tags' in config:
            self.tags = self.machine.string_to_list(config['tags'])
        if 'label' in config:
            self.label = config['label']  # todo change to multi lang
        # todo more pythonic way, like self.label = blah if blah?

        # Add this instance to our dictionary for this type of device
        if collection != -1:
            # Have to use -1 here instead of None to catch an empty collection
            collection[name] = self


class Switch(HardwareObject):
    """ A switch in a pinball machine.

    """

    log = logging.getLogger("Switch")

    def __init__(self, machine, name, config, collection=None):
        super(Switch, self).__init__(machine, name, config, collection)

        self.machine = machine
        self.name = name
        self.config = config
        self.state = 0
        """ The logical state of a switch. 1 = active, 0 = inactive. This takes
        into consideration the NC or NO settings for the switch."""
        self.hw_state = 0
        """ The physical hardware state of the switch. 1 = active,
        0 = inactive. This is what the actual hardware is reporting and does
        not consider whether a switch is NC or NO."""

        # todo read these in and/or change to dict
        self.type = 'NO'
        """ Specified whether the switch is normally open ('NO', default) or
        normally closed ('NC')."""
        if 'type' in config and config['type'] == 'NC':
            self.type = 'NC'

        self.debounce = True
        """ Specifies whether the hardware should debouce this switch before
        reporting a state change to the host computer. Default is True."""
        if 'debouce' in config and config['debouce'] == 'False':
            self.debouce = False

        self.last_changed = None
        self.hw_timestamp = None

        self.log.debug("Creating '%s' with config: %s", name, config)
        self.hw_switch, self.number, self.hw_state = self.machine.platform.\
            configure_switch(self.config['number'], self.debounce)

        self.log.debug("Current hardware state of switch '%s': %s",
                       self.name, self.hw_state)

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


class Driver(HardwareObject):
    """Generic class that holds driver objects.

    A 'driver' is any device controlled from a driver board which is typically
    the high-voltage stuff like coils and flashers.

    This class exposes the methods you can use on these driver types of
    devices. Each platform module (i.e. P-ROC, FAST, etc.) subclasses this
    class to actually communicate with the physitcal hardware and perform the
    actions.

    """

    log = logging.getLogger("Driver")

    def __init__(self, machine, name, config, collection=None):
        super(Driver, self).__init__(machine, name, config, collection)

        # todo read these in and/or change to dict
        self.pulse_time = 30
        self.pwm_on = 0
        self.pwm_off = 0

        self.hw_driver = self.machine.platform.configure_driver(
            self.config['number'])
        self.log.debug("Creating '%s' with config: %s", name, config)

        '''
        if klass == PROCDriver:
                            if 'pulseTime' in item_dict:
                                item.parent.pulse_time = item_dict['pulseTime']
                            if 'polarity' in item_dict:
                                item.reconfigure(item_dict['polarity'])
                            if 'holdPatter' in item_dict:
                                item.parent.pwm_on = int(item_dict['holdPatter'].split('-')[0])
                                item.parent.pwm_off = int(item_dict['holdPatter'].split('-')[1])
                                '''

    def disable(self):
        """ Disables this driver """
        self.log.debug("Disabling Driver: %s", self.name)
        self.time_last_changed = time.time()
        # todo , now do it
        # todo also disable the timer which reenables this

    def pulse(self, milliseconds=None):
        """ Enables this driver.

        Parameters
        ----------

        milliseconds : int : optional
            The number of milliseconds the driver should be enabled for. If no
            value is provided, the driver will be enabled for the value
            specified in the config dictionary.

        """
        if milliseconds is None:
            milliseconds = self.pulse_time
        elif milliseconds < 1:
            self.log.warning("Received command to pulse  Driver %s for %dms, "
                             "but ms is less than 1, so we're doing nothing.",
                             self.name, milliseconds)
            return
        # todo also disable the timer which reenables this
        self.log.debug("Pulsing Driver %s for %dms", self.name, milliseconds)
        self.hw_driver.pulse(int(milliseconds))
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


class Light(HardwareObject):
    """ Parent class of "lights" in a pinball machine.

    These can either be traditional incandescent lamps (or replacement LEDs)
    connected to a lamp matrix, or they can be LEDs connected to an LED
    control board.
    """
    def __init__(self):
        self.log = logging.getLogger('HardwareMatrixLight')


class MatrixLight(Light):
    """ Represents a light connected to a traditional lamp matrix in a pinball
    machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.

    Note you cannot control brightness on these. They're either "on" or "off."
    Also you can't control the color. (Color is dictated by the color of the
    light and/or the color of the plastic insert or cap.)

    For "new-style" directly-addressable multi-color LEDs (which are connected
    to an LED board instead of a lamp matrix), use `class:HardwareDirectLED`.
    """

    def __init__(self):
        self.log = logging.getLogger('HardwareMatrixLight')

    def enable(self):
        pass

    def disable(self):
        pass


class DirectLED(Light):
    """ Represents an LED connected to an LED interface board.

    This LED can have any number of elements. Typically they're either single
    element (single color), or three element (RGB), though dual element
    (red/green) and quad-element (RGB + UV) also exist and can be used.

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
        """ Set an LED to a color.

        Parameters
        ----------

        color

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


class HardwareDict(dict):
    """A collection of HardwareObjects.

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
        # None, and we can't call this HardwareDict on None. Maybe make
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
