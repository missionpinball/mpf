"""Contains the MoveOut transition class."""
# move_out.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import time
import pygame


from mpf.system.timing import Timing
from mpf.media_controller.core.display import Transition


class MoveOut(Transition):
    """Move Out Transition. The current slide moves out, revealing the new slide
        underneath.

    Args:
        mpfdisplay: The MPFDIsplay this transition is applying to.
        machine: The main machine object.
        slide_a: Slide object representing the existing (current) slide.
        slide_b: Slide object representing the incoming (new) slide.
        duration: MPF time string of the how long this transition should take.
        direction: String which defines which direction the current slide will
            move out. Options are 'top', 'bottom', 'left' and 'right'
        **kwargs: Not used but needed because there might be extra kwargs
            depending on how this transition is called.

    """

    def __init__(self, mpfdisplay, machine, priority, mode, slide_a, slide_b,
                 duration='1s', direction='top', **transition_settings):
        # Assumes slides are the same size

        super(MoveOut, self).__init__(mpfdisplay=mpfdisplay,
                                     machine=machine,
                                     priority=priority,
                                     mode=mode,
                                     slide_a=slide_a,
                                     slide_b=slide_b,
                                     duration=duration,
                                     **transition_settings)

        self.slide_a_end_y = 0
        self.slide_a_end_x = 0

        # calculate the ending slide_a position
        if direction == 'top':
            self.slide_a_end_y = -self.slide_a.surface.get_height()
        elif direction == 'bottom':
            self.slide_a_end_y = self.slide_a.surface.get_height()
        elif direction == 'left':
            self.slide_a_end_x = -self.slide_a.surface.get_width()
        elif direction == 'right':
            self.slide_a_end_x = self.slide_a.surface.get_width()

        self.slide_a_current_x = 0
        self.slide_a_current_y = 0

    def update(self):
        """Called each display loop to update the slide positions."""
        super(MoveOut, self).update()

        # figure out which direction is non-zero and move it towards zero

        if ((self.slide_a_end_x > 0 and
                self.slide_a_current_x < self.slide_a_end_x) or
               (self.slide_a_end_x < 0 and
                self.slide_a_current_x > self.slide_a_end_x)):
            self.slide_a_current_x = int(
                self.slide_a_end_x * self.percent)

        if ((self.slide_a_end_y > 0 and
                self.slide_a_current_y < self.slide_a_end_y) or
               (self.slide_a_end_y < 0 and
                self.slide_a_current_y > self.slide_a_end_y)):
            self.slide_a_current_y = int(
                self.slide_a_end_y * self.percent)

        try:  # try in case super() completed the transition
            # blit slide_b as the background
            self.surface.blit(self.slide_b.surface, (0, 0))

            # blit slide_a on top of it
            self.surface.blit(self.slide_a.surface,
                              (self.slide_a_current_x, self.slide_a_current_y))
        except (TypeError, AttributeError):
            pass

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
