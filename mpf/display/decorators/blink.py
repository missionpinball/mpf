"""Blink Decorator."""
# blink.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import pygame
import pygame.locals
import time

from mpf.system.display import Decorator


class Blink(Decorator):
    """Blink decorator which causes the element it's applied to to blink on and
    off.

    Args:
        parent_element: The DisplayElement object this decorator is applied to.
        on_secs: The number of seconds for the "on" portion of the blinking.
            Default is 0.2.
        off_secs: The number of seconds for the "off" porition of the blinking.
            Default is 0.2.
        repeats: The number of times you'd like this element to blink. A value
            of -1 means it will repeat forever.

    Attributes:
        parent_element: The DisplayElement object this decorator is applied to.
        on_secs: The number of seconds for the "on" portion of the blinking.
        off_secs: The number of seconds for the "off" porition of the blinking.
        repeats: The number of remaining blinks this element will do. A value
            of -1 means it will repeat forever.
        dirty: Boolean which specifies whether this decorator needs to apply
            an update to the parent_element in this frame.
        current_state: 1 means this decorator is in the "on" phase of a blink,
            0 means it's in the "off" phase of a blink.
        next_action_time: Real-world time of when the next state change of this
            decorator will be.
    """

    def __init__(self, parent_element, on_secs=.2, off_secs=.2, repeats=-1,
                 **kwargs):
        self.next_action_time = 0
        self.current_state = 1
        self.on_secs = on_secs
        self.off_secs = off_secs
        self.repeats = repeats
        self.parent_element = parent_element

    @property
    def dirty(self):
        if self.next_action_time <= time.time():
            return True
        else:
            return False

    def update(self):
        """Updates the parent_element if it's time to blink. Can safely be
        called often.

        Returns: True if this decorator made a change to the element that has to
            be re-blitted. False if no change.
        """
        current_time = time.time()
        if self.next_action_time <= current_time:
            if self.current_state:
                self.parent_element.opacity = 0
                self.current_state = 0
                self.next_action_time = current_time + self.off_secs

                if self.repeats == 0:
                    self.unload()
                elif self.repeats > 0:
                    self.repeats -= 1

            else:
                self.current_state = 1
                self.next_action_time = current_time + self.on_secs
                self.parent_element.opacity = 255

            return True

        return False

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
