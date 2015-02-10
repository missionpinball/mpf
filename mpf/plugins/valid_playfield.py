"""MPF plugin that handles valid playfield tracking for a pinball machine."""
# valid_playfield.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


# todo

# hook ball add live to setup vpf checking

import logging


def preload_check(machine):
    return True


class ValidPlayfield(object):
    """Base class for a valid playfield checking module.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('ValidPlayfield')

        self.hits_needed = 0
        self.hits_so_far = 0
        self.flag_valid_playfield = False

    def enable(self):
        """Sets up the valid playfield checking."""

        self.hits_so_far = 0
        self.machine.events.add_handler("sw_playfield_active",
                                        self.live_hit)
        # Watch for a ball drain event so we can intercept it
        self.machine.events.add_handler("ball_drain",
                                        self.drain)
        self.machine.events.add_handler('sw_validPlayfield',
                                        self.validate_playfield, 1000.0)
        # valid playfield at priority 1000 so we validate first.

    def live_hit(self):
        """Called whenever a switch couting towards valid playfield is hit."""

        if not self.flag_valid_playfield:
            self.hits_so_far += 1
            self.log.debug("Received a switch hit towards valid playfield. "
                           "Total needed: %s, So far: %s", self.hits_needed,
                           self.hits_so_far)
            if self.hits_so_far >= self.hits_needed:
                self.validate_playfield()
        else:  # pf is valid, so why are we here?
            self.log.warning("Received a live_hit, but pf is "
                             "already valid. Something's messed up.")
            self.remove()

    def drain(self, balls):
        """Handler for the ball_drain relay event which is called when a ball
        drains when the playfield is not valid."""

        # We want to prevent ball_remove_live from being called, but we also
        # have to get a new ball launched. So we're going to stealth & auto
        # add new ball(s) into play.

        self.machine.playfield.add_ball()
        # Todo should we specify the device here?

        # Since the playfield is not valid, we 'take' all the balls here so
        # there are none left to be processed by the ball drain.
        return {'balls': 0}

    def validate_playfield(self):
        """Validates the playfield, but only if it was not valid before."""

        self.remove()
        if not self.flag_valid_playfield:
            self.flag_valid_playfield = True
            self.machine.events.post('playfield_valid')
            # todo add start ball save (based on the event, not here)

    def remove(self):
        """Cancels and removews the valid playfield verification checking."""

        # todo add this into ball ending

        self.log.debug("Removing the valid playfield checking")
        self.machine.events.remove("sw_playfield_active", self.live_hit)
        self.machine.events.remove("sw_playfield_active", self.drain)

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
