""" Contains the MatrixLight parent classes. """
# light.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device


class MatrixLight(Device):
    """ Represents a light connected to a traditional lamp matrix in a pinball
    machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.

    """

    config_section = 'MatrixLights'
    collection = 'lights'

    #todo need to get the handler stuff out of each of these I think and into
    # a parent class? Maybe this is a device thing?

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Light.' + name)

        self.log.debug('Creating device with config: %s', config)

        super(MatrixLight, self).__init__(machine, name, config, collection)

        # We save out number_str since the platform driver will convert the
        # number into a hardware number, but we need the original number for
        # some things later.
        self.config['number_str'] = str(config['number']).upper()

        self.hw_driver, self.number = self.machine.platform.configure_matrixlight(self.config)

        self.registered_handlers = []

        self.state = {  # current state of this light
                        'brightness': 0,
                        'priority': 0}

        self.cache = {  # cached state of last manual command
                        'brightness': 0,
                        'priority': 0}

        # set up the X, Y coordinates
        self.x = None
        self.y = None

        if 'x' in config:
            self.x = config['x']

        if 'y' in config:
            self.y = config['y']



        # register for action events
        self.machine.events.add_handler('action_light_' + self.name + '_on',
                                        self.on)
        self.machine.events.add_handler('action_light_' + self.name + '_off',
                                        self.off)

    def on(self, brightness=255, fade_ms=0, start_brightness=None,
           priority=0, cache=True, force=False):

        # First, if this incoming command is at a lower priority than what the
        # light is doing now, we don't proceed
        if priority < self.state['priority'] and not force:
            return

        # todo cache support
        # todo add brightness 0 as the same as on(0)
        if type(brightness) is list:
            brightness = brightness[0]

        if self.registered_handlers:
            for handler in self.registered_handlers:
                handler(light_name=self.name, brightness=brightness)

        self.state['brightness'] = brightness
        self.state['priority'] = priority

        if cache:
            self.cache['brightness'] = brightness
            self.cache['priority'] = priority

        self.hw_driver.on(brightness, fade_ms, start_brightness)

    def off(self, fade_ms=0, priority=0, cache=True, force=False):
        self.on(brightness=0, fade_ms=fade_ms, priority=priority, cache=cache,
                force=force)

    def add_handler(self, callback):
        """Registers a handler to be called when this light changes state."""
        self.registered_handlers.append(callback)

    def remove_handler(self, callback=None):
        """Removes a handler from the list of registered handlers."""
        if not callback:  # remove all
            self.registered_handlers = []
            return

        if callback in self.registered_handlers:
            self.registered_handlers.remove(callback)

    def restore(self, force=False):
        """Restores the light state from cache."""

        # todo revisit force

        # if self.cache['priority'] >= self.state['priority'] or force is True:

        self.on(brightness=self.cache['brightness'],
                priority=self.cache['priority'],
                force=True)


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
