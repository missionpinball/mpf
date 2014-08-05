""" Contains the DirectLED parent class. """
# led.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.hardware import Device


class DirectLED(Light):
    """ Represents an LED connected to an LED interface board.

    This LED can have any number of elements. Typically they're either single
    element (single color), or three element (RGB), though dual element
    (red/green) and quad-element (RGB + UV) also exist and can be used.

    """
    def __init__(self, machine, name, number, platform_driver):
        self.log = logging.getLogger('LED.' + name)
        super(DirectLED, self).__init__(self, machine, name, number)
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
