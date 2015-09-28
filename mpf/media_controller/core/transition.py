"""Contains the Transition base class."""

# transition.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import time
from mpf.media_controller.core.slide import Slide
from mpf.system.timing import Timing


class Transition(Slide):
    """Parent class for all slide Transition objects. Subclasses Slide.

    Args:
        mpfdisplay: The MPFDisplay object this transition is for.
        machine: The main MachineController object.
        slide_a: The current (outgoing) Slide.
        slide_b: The new (incoming) Slide.
        duration: MPF timing string for how long this transition will take.
            Default is 1 second.
        **kwargs: Any additional key/value settings for this transition. (All
            transitions are different and have different settings.)

    Attributes:
        slide_a: Outgoing slide.
        slide_b: Incoming slide.
        duration: Duration in seconds (float or int).
        start_time: Real world time when this transition began.
        end_time: Real world time when this transition will complete.
    """

    def __init__(self, mpfdisplay, machine, priority,
                 mode, slide_a, slide_b, duration='1s', **kwargs):

        super(Transition, self).__init__(mpfdisplay=mpfdisplay,
                                         machine=machine,
                                         priority=priority,
                                         mode=mode)

        self.slide_a = slide_a
        self.slide_b = slide_b
        self.priority = slide_b.priority
        self.duration = Timing.string_to_secs(duration)
        self.active_transition = True
        self.slide_a.active_transition = True
        self.slide_b.active_transition = True
        self.name = str(slide_a.name) + "_transition_" + str(slide_b.name)

        self.start_time = time.time()
        self.end_time = self.start_time + self.duration

        # mark both slides as active
        self.slide_a.active = True
        self.slide_b.active = True

        # Need to set the initial surface of the transition slide to the
        # existing slide's surface since the transition slide will be active
        self.surface.blit(self.slide_a.surface, (0, 0))

        # todo if an element is not loaded on the B slide when this transition
        # is called, it will crash. Need to probably not call transition
        # directly and switch to some kind of loader method for it that can
        # delay this as needed.

    def update(self):
        """Called to update the slide with the latest transition animation.

        Completely replaces the update() method in the parent class since the
        transition class is a special type of slide.

        """
        # Update the slides (so animations keep playing during the transition)

        # self.slide_a.update()
        # self.slide_b.update()

        try:
            self.slide_a.update()
        except AttributeError:
            #self.complete()
            pass

        try:
            self.slide_b.update()
        except AttributeError:
            #self.complete()
            pass

        # figure out what percentage along we are
        self.percent = (time.time() - self.start_time) / self.duration

        if self.percent >= 1.0:
            self.complete()

        # don't set self._dirty since this transition slide is always dirty as
        # long as it's active

    def complete(self):
        """Mark this transition as complete."""
        # this transition is done
        self.active_transition = False

        try:
            self.slide_a.active_transition = False
        except AttributeError:
            pass

        self.mpfdisplay.remove_slide(self.slide_a, refresh_display=False)
        self.remove()

        try:
            self.slide_b.active_transition = False
        except AttributeError:
            pass


        # Can't clear the transition on the b slide until after the others are
        # removed or else the refresh will kill this one.

        self.mpfdisplay.transition_complete()

        self.slide_a = None
        self.slide_b = None


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
