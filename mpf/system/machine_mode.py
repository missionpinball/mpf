# machine_mode.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework
import logging
from mpf.system.tasks import DelayManager, Task


class MachineMode(object):
    """ A machine mode represents as special modes, the idea is there's only
    one at a time.

    You can specify an order so that when one ends, the next one starts.

    Examples:
        *Attract
        *Game
        *Match
        *Highscore Entry
        *Service

    The idea is the machine modes will control the buttons since they do
    different things in different modes. ("Buttons" versus "Switches" in this
    case. Buttons are things that players can control, like coin switches,
    control panel buttons, flippers, start, plunge, etc.)
    """

    def __init__(self, machine):
        self.log = logging.getLogger(__name__)
        self.machine = machine
        self.task = None
        self.delays = DelayManager()
        self.registered_event_handlers = []

    def start(self):
        """Starts this machine mode. """
        self.log.info("Mode started")
        self.active = True
        self.task = Task.Create(self.tick, sleep=0)

    def stop(self):
        """Stops this machine mode. """

        self.log.debug("Stopping...")
        self.ative = False
        # clear delays
        self.log.debug("Removing scheduled delays")
        self.delays.clear()

        # deregister event handlers
        self.log.debug("Removing event handlers")
        for handler in self.registered_event_handlers:
            self.machine.events.remove_handler(handler)
        self.log.debug("Stopped")

    def tick(self):
        """Most likely you'll just copy this entire method to your mode
        subclass. No need for super().
        """
        while self.active:
            # do something here
            yield

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
