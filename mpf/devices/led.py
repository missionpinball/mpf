""" Contains the LED parent classes. """
# leds.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time

from mpf.system.devices import Device
from mpf.system.tasks import Task


class LED(Device):
    """ Represents an light connected to an new-style interface board.
    Typically this is an LED.

    DirectLEDs can have any number of elements. Typically they're either
    single element (single color), or three element (RGB), though dual element
    (red/green) and quad-element (RGB + UV) also exist and can be used.

    """

    config_section = 'LEDs'
    collection = 'leds'

    @classmethod
    def device_class_init(cls, machine):
        if 'brightness_compensation' in machine.config['Hardware']:
            machine.config['Hardware']['brightness_compensation'] = (
                float(machine.config['Hardware']['brightness_compensation']))
        else:
            machine.config['Hardware']['brightness_compensation'] = 1.0

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('LED.' + name)
        super(LED, self).__init__(machine, name, config, collection)

        # We save out number_str since the platform driver will convert the
        # number into a hardware number, but we need the original number for
        # some things later.
        self.config['number_str'] = str(config['number']).upper()

        self.hw_driver = self.machine.platform.configure_led(self.config)

        self.fade_in_progress = False
        self.fade_task = None
        self.fade_destination_color = [0.0, 0.0, 0.0]
        self.fade_end_time = None

        self.state = {  # current state of this LED
                        'color': [0.0, 0.0, 0.0],
                        'priority': 0,
                        'destination_color': [0.0, 0.0, 0.0],
                        'destination_time': 0.0,
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

        if 'brightness_compensation' not in self.config:
            self.config['brightness_compensation'] = [1.0, 1.0, 1.0]
        else:
            # make sure our config string is a list
            self.config['brightness_compensation'] = (
                self.machine.string_to_list(
                    self.config['brightness_compensation']))
            # if there's only one value in the list, use it for all the elements
            if len(self.config['brightness_compensation']) == 1:
                self.config['brightness_compensation'].extend(
                    [self.config['brightness_compensation'][0],
                     self.config['brightness_compensation'][0]])
            # if there are only two elements, use 1.0 for the third.
            elif len(self.config['brightness_compensation']) == 2:
                self.config['brightness_compensation'].append(1.0)
            # make sure they're all floats
            for i in range(3):
                self.config['brightness_compensation'][i] = (
                    float(self.config['brightness_compensation'][i]))

        if 'fade_ms' not in self.config:
            self.config['fade_ms'] = None

        self.current_color = []  # one item for each element, 0-255

    def color(self, color, fade_ms=None, brightness_compensation=True,
              priority=0, cache=True, force=False):
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
                If the priority is negative, it will force this color to be
                applied now
        """

        # If the incoming priority is lower that what this LED is at currently
        # ignore this request.
        if priority < self.state['priority'] and not force:
            return

        if brightness_compensation:
            color = self.compensate(color)

        if fade_ms is None:
            if self.config['fade_ms'] is not None:
                fade_ms = self.config['fade_ms']
            elif self.machine.config['LEDSettings']:
                fade_ms = (self.machine.config['LEDSettings']
                           ['default_led_fade_ms'])
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

        else:
            self.hw_driver.color(color)
            self.state['color'] = color

        if cache:
            self.cache['color'] = color  # new color
            self.cache['fade_ms'] = fade_ms
            self.cache['priority'] = priority
            self.cache['destination_color'] = priority
            self.cache['destination_time']
            self.cache['start_color'] = self.cache['color']
            self.cache['start_time'] = time.time()

    def disable(self):
        """ Disables an LED, including all elements of a multi-color LED.
        """
        self.color([0.0, 0.0, 0.0], 0, False, -1)

    def get_state(self):
        """Returns the current state of this LED"""
        return self.state

    def restore(self):
        """Sets this LED to the cached state."""
        self.color(color=self.cache['color'],
                   fade_ms=0,
                   brightness_compensation=False,  # cached value includes this
                   priority=self.cache['priority'],
                   force=False)

    def compensate(self, color):
        """Applies the current brightness compensation values to the passed
        color.

        Args:
            color: a 3-item color list of ints

        Returns:
            The brightness-compensated 3-item color list of ints
        """

        global_settings = self.machine.config['LEDSettings']

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
            self.fade_task = Task.Create(self._fade_task)

    def _fade_task(self):
        while self.fade_in_progress:

            state = self.state

            # figure out the ratio of how far along we are
            ratio = ((time.time() - state['start_time']) /
                     (state['destination_time'] - state['start_time']))

            new_color = list()

            if ratio >= 1.0:  # fade is done
                self.fade_in_progress = False
                new_color = state['destination_color']

            else:
                new_color.append(int((state['destination_color'][0] * ratio) +
                                 state['start_color'][0]))
                new_color.append(int((state['destination_color'][1] * ratio) +
                                 state['start_color'][1]))
                new_color.append(int((state['destination_color'][2] * ratio) +
                                 state['start_color'][2]))

            self.color(new_color, 0, False, state['priority'], False)
            yield

    def _kill_fade(self):
        self.fade_in_progress = False

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
