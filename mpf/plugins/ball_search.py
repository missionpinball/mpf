"""MPF plugin for a ball search module which actually controls the coils to
search for a missing pinball.

This module is not yet complete and does not work.

"""
# ball_search.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.tasks import Task
from mpf.system.timing import Timing


def preload_check(machine):

    return True


class BallSearch(object):
    """Base class which implements the ball search functionality.

    This module is responsible for actually firing the coils and moving motors,
    etc. when the ball search begins. It can respond to multiple "phases" of
    ball search. (For example, for the few round it might only do easy things
    like fire pop bumpers. If it doesn't find the ball after that, it will
    start trying to eject balls from ball devices.)

    This ball search module is not responsible for deciding to start or stop
    a ball search--that is something that Ball Controller does. Also this ball
    search module doesn't know when a ball is actually found. If a playfield
    switch is hit then the ball live event will be raised and the ball
    controller will tell this ball search module that it can stop looking.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine):
        self.log = logging.getLogger('ballsearch')
        self.machine = machine
        self.active = False

        # Setup ball search coils
        self.ball_search_coils = []
        for coil in self.machine.coils.items_tagged('ballSearch'):
            self.ball_search_coils.append(coil)
        self.log.debug("Found %s ball search coils",
                       len(self.ball_search_coils))

        # Register for ball search-related events
        self.machine.events.add_handler("ball_search_begin_phase1", self.start)
        self.machine.events.add_handler("ball_search_begin_phase2", self.start)
        self.machine.events.add_handler("ball_search_end", self.end)

    def start(self):
        """Begin the ball search process"""
        self.log.debug("Starting the ball search")

        self.active = True
        self.task = Task.Create(self.tick)

    def end(self):
        """Ends the active ball search."""
        self.log.debug("Stopping the ball search")
        self.active = False

    def tick(self):
        """Method that runs as a task """
        while self.active:
            for coil in self.ball_search_coils:
                self.pop_coil(coil)
                yield Timing.secs(self.machine.config['ballsearch']\
                    ['secs between ball search coils'])
            yield Timing.secs(self.machine.config['ballsearch']\
                    ['secs between ball search rounds'])
        # todo do we have to deal with switches that might be hit due to these
        # coils firing?
        # todo should the above code also look for self.active?

    def pop_coil(self, coil):
        """Sctviates the 'coil' based on it's default pulse time. Holds a coil
        open for the hold time in sec.

        This is not yet implemented. (It's copied in from our ball_controller
        code from our old python project.)
        """
        '''
        if coil.patter_on:
            coil.patter(on_ms=coil.patter_on,
                        off_ms=coil.patter_off,
                        original_on_ms=coil.default_pulse_ms,
                        now=True)
            self.log.debug("Ball Search is holding coil %s for %ss",
                             coil.name, coil.search_hold_time)
            # set a delay to turn off the coil if it's a hold coil
            self.delay(name="Ball_Search_Release", delay=coil.search_hold_time,
                       callback=self.machine.proc.driver_disable,
                       param=coil.number)
            # todo change above to platform
        elif coil.default_pulse_ms:
            # if it's not a hold coil, just pulse it with the default
            coil.pulse()
            self.log.debug("Ball Search is pulsing coil %s", coil.name)
        '''

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
