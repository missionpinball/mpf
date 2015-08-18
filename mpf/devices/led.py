""" Contains the LED parent classes. """
# led.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time

from mpf.system.device import Device
from mpf.system.tasks import Task
from mpf.system.config import Config


class LED(Device):
    """ Represents an light connected to an new-style interface board.
    Typically this is an LED.

    DirectLEDs can have any number of elements. Typically they're either
    single element (single color), or three element (RGB), though dual element
    (red/green) and quad-element (RGB + UV) also exist and can be used.

    """

    config_section = 'leds'
    collection = 'leds'
    class_label = 'led'

    @classmethod
    def device_class_init(cls, machine):
        if 'brightness_compensation' in machine.config['hardware']:
            machine.config['hardware']['brightness_compensation'] = (
                float(machine.config['hardware']['brightness_compensation']))
        else:
            machine.config['hardware']['brightness_compensation'] = 1.0

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('LED.' + name)
        config['number_str'] = str(config['number']).upper()
        super(LED, self).__init__(machine, name, config, collection,
                                  platform_section='leds')

        self.log.debug("Creating '%s' with config: %s", name, config)

        self.config['default_color'] = Config.hexstring_to_list(
            input_string=self.config['default_color'],
            output_length=3)

        self.hw_driver = self.platform.configure_led(self.config)

        self.fade_in_progress = False
        self.fade_task = None
        self.fade_destination_color = [0.0, 0.0, 0.0]
        self.fade_end_time = None

        self.state = {  # current state of this LED
                        'color': [0.0, 0.0, 0.0],
                        'priority': 0,
                        'destination_color': [0.0, 0.0, 0.0],
                        'destination_time': 0.0,
                        'start_color': [0.0, 0.0, 0.0],
                        'start_time': 0.0
                     }

        self.cache = {  # cached state of last manual command
                        'color': [0.0, 0.0, 0.0],
                        'priority': 0,
                        'destination_color': [0.0, 0.0, 0.0],
                        'destination_time': 0.0,
                        'start_color': [0.0, 0.0, 0.0],
                        'start_time': 0.0
                     }

        self.set_brightness_compensation(self.config['brightness_compensation'])

        self.current_color = []  # one item for each element, 0-255

        if self.debug:
            self.log.debug("Intial settings: %s", self.config)

    def set_brightness_compensation(self, value):
        """Sets the brightness compensation for this LED.

        args:
            value: Str or list (of 1-to-3 items) of the new brightness
                compensation value to set. List items are floats. 1.0 is
                standard full brightness. 0.0 is off. 2.0 is 200% brightness
                (which only comes into play if the LED is not at full
                brightness). If the value is a string, it's converted to a list,
                broken by commas.

        The brightness compensation list is three items long, one for each RGB
        element. If the LED has less than three elements, additional values are
        ignored.

        If the value list is only one item, that value is used for all three
        elements.

        If the value list is two items, a value of 1.0 is used for the third
        item.

        """
        if type(value) is not list:
            value = Config.string_to_list(value)

        value = [float(x) for x in value]

        if len(value) == 1:
            value.extend([value[0], value[0]])
        elif len(value) == 2:
            value.append(1.0)

        self.config['brightness_compensation'] = value

    def color(self, color, fade_ms=None, brightness_compensation=True,
              priority=0, cache=True, force=False, blend=False):
        """Sets this LED to the color passed.

        Args:
            color: a list of integers which represent the red, green, and blue
                values the LED will be set to. If this list is fewer than three
                items, it assumes zeros for the rest.
            fade_ms: Integer value of how long the LED should fade from its
                current color to the color you're passing it here.
            brightness_compensation: Boolean value which controls whether this
                LED will be light using the current brightness compensation.
                Default is True.
            priority: Arbitrary integer value of the priority of this request.
                If the incoming priority is lower than the current priority,
                this incoming color request will have no effect. Default is 0.
            cache: Boolean which controls whether this new color command will
                update the LED's cache. Default is True.
            force: Boolean which will force this new color command to be applied
                to the LED, regardless of the incoming or current priority.
                Default is True.
            blend: Not yet implemented.
        """

        if self.debug:
            self.log.debug("+------Received new color command---------")
            self.log.debug("| color: %s", color)
            self.log.debug("| priority: %s", priority)
            self.log.debug("| cache: %s", cache)
            self.log.debug("| force: %s", force)
            self.log.debug("| fade_ms: %s", fade_ms)
            self.log.debug("| blend: %s", blend)
            self.log.debug("| brightness_compensation: %s",
                          brightness_compensation)

            self.log.debug("+-------------Current State---------------")
            self.log.debug("| color: %s", self.state['color'])
            self.log.debug("| priority: %s", self.state['priority'])
            self.log.debug("| destination_color: %s",
                          self.state['destination_color'])
            self.log.debug("| destination_time: %s",
                          self.state['destination_time'])
            self.log.debug("| start_color: %s", self.state['start_color'])
            self.log.debug("| start_time: %s", self.state['start_time'])
            self.log.debug("+-----------------------------------------")

        # If the incoming priority is lower that what this LED is at currently
        # ignore this request.
        if priority < self.state['priority'] and not force:

            if self.debug:
                self.log.debug("Incoming color priority: %s. Current priority: "
                              " %s. Not applying update.", priority,
                              self.state['priority'])
            return

        elif self.debug:
            self.log.debug("Incoming color priority: %s. Current priority: "
                          " %s. Processing new command.", priority,
                          self.state['priority'])

        if brightness_compensation:
            color = self.compensate(color)

        # make sure we have a list of three ints
        color = [int(x) for x in color]
        color.extend([0] * 3-len(color))

        if fade_ms is None:
            if self.config['fade_ms'] is not None:
                fade_ms = self.config['fade_ms']
                if self.debug:
                    self.log.debug("Incoming fade_ms is none. Setting to %sms "
                                  "based on this LED's default fade config",
                                  fade_ms)
            elif self.machine.config['led_settings']:
                fade_ms = (self.machine.config['led_settings']
                           ['default_led_fade_ms'])
                if self.debug:
                    self.log.debug("Incoming fade_ms is none. Setting to %sms "
                                  "based on this global default fade", fade_ms)
            # potentional optimization make this not conditional

        current_time = time.time()

        # update our state
        self.state['priority'] = priority

        if fade_ms:
            self.state['destination_color'] = color
            self.state['destination_time'] = current_time + (fade_ms / 1000.0)
            self.state['start_color'] = self.state['color']
            self.state['start_time'] = current_time
            self._setup_fade()

            if self.debug:
                print "we have a fade to set up"

        else:
            self.hw_driver.color(color)
            self.state['color'] = color

            if self.debug:
                self.log.debug("Setting Color: %s", color)

        if cache:
            self.cache['color'] = color  # new color
            self.cache['fade_ms'] = fade_ms
            self.cache['priority'] = priority
            self.cache['destination_color'] = priority
            self.cache['destination_time']
            self.cache['start_color'] = self.cache['color']
            self.cache['start_time'] = time.time()

        if self.debug:
            self.log.debug("+---------------New State-----------------")
            self.log.debug("| color: %s *******************", self.state['color'])
            self.log.debug("| priority: %s", self.state['priority'])
            self.log.debug("| new fade: %s", fade_ms)
            self.log.debug("| start_color: %s", self.state['start_color'])
            self.log.debug("| destination_color: %s",
                          self.state['destination_color'])
            self.log.debug("| start_time: %s", self.state['start_time'])
            self.log.debug("| current_time: %s", time.time())
            self.log.debug("| destination_time: %s",
                          self.state['destination_time'])
            self.log.debug("+-----------------------------------------")
            self.log.debug("==========================================")

    def disable(self, fade_ms=0, priority=0, cache=True, force=False):
        """ Disables an LED, including all elements of a multi-color LED.
        """
        self.color(color=[0, 0, 0], fade_ms=fade_ms, priority=priority,
                   cache=cache, force=force)

    def on(self, brightness=255, fade_ms=0, start_brightness=None,
           priority=0, cache=True, force=False):

        self.color(color=[self.config['default_color'][0] * brightness / 255.0,
                          self.config['default_color'][1] * brightness / 255.0,
                          self.config['default_color'][2] * brightness / 255.0],
                   fade_ms=fade_ms,
                   priority=priority,
                   cache=cache,
                   force=force)

    def off(self, fade_ms=0, priority=0, cache=True, force=False):
        self.color(color=[0, 0, 0], fade_ms=fade_ms, priority=priority,
                   cache=cache, force=force)
        # todo send args to disable()

    def get_state(self):
        """Returns the current state of this LED"""
        return self.state

    def restore(self):
        """Sets this LED to the cached state."""

        if self.debug:
            self.log.debug("Received a restore command.")
            self.log.debug("Cached color: %s, Cached priority: %s",
                          self.cache['color'], self.cache['priority'])

        self.color(color=self.cache['color'],
                   fade_ms=0,
                   brightness_compensation=False,  # cached value includes this
                   priority=self.cache['priority'],
                   force=True,
                   cache=True)

    def compensate(self, color):
        """Applies the current brightness compensation values to the passed
        color.

        Args:
            color: a 3-item color list of ints

        Returns:
            The brightness-compensated 3-item color list of ints
        """

        global_settings = self.machine.config['led_settings']

        color[0] = (int(color[0] *
                    self.config['brightness_compensation'][0] *
                    global_settings['brightness_compensation']))
        color[1] = (int(color[1] *
                    self.config['brightness_compensation'][1] *
                    global_settings['brightness_compensation']))
        color[2] = (int(color[2] *
                    self.config['brightness_compensation'][2] *
                    global_settings['brightness_compensation']))

        return color

    def _setup_fade(self):
        self.fade_in_progress = True

        if not self.fade_task:
            if self.debug:
                print "setting up fade task"
            self.fade_task = Task.Create(self._fade_task)
        elif self.debug:
                print "already have a fade task"

    def _fade_task(self):
        while self.fade_in_progress:

            if self.debug:
                print "fade_in_progress fade_task"
                print "state", self.state

            state = self.state

            # figure out the ratio of how far along we are
            ratio = ((time.time() - state['start_time']) /
                     (state['destination_time'] - state['start_time']))

            new_color = list()

            if self.debug:
                print "ratio", ratio

            if ratio >= 1.0:  # fade is done
                self.fade_in_progress = False
                new_color = state['destination_color']

            else:
                new_color.append(int(((state['destination_color'][0] - state['start_color'][0]) * ratio) + state['start_color'][0]))
                new_color.append(int(((state['destination_color'][1] - state['start_color'][1]) * ratio) + state['start_color'][1]))
                new_color.append(int(((state['destination_color'][2] - state['start_color'][2]) * ratio) + state['start_color'][2]))

            if self.debug:
                print "new color", new_color

            self.color(color=new_color, fade_ms=0,
                       brightness_compensation=False,
                       priority=state['priority'], cache=False)

            yield

        if self.debug:
            print "fade_in_progress just ended"
            print "killing fade task"

        self.fade_task = None
        raise StopIteration()

    def _kill_fade(self):
        self.fade_in_progress = False



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
