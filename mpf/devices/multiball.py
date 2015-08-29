""" Contains the MultiBall device class."""
# multiball.py
# Mission Pinball Framework
# MPF is written by Brian Madden & Gabe Knuth
# This module was originally written by Jan Kantert
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.device import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.config import Config

class Multiball(Device):

    config_section = 'multiballs'
    collection = 'multiballs'
    class_label = 'multiball'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(Multiball, self).__init__(machine, name, config, collection,
                                        validate=validate)

        self.delay = DelayManager()

        # let ball devices initialise first
        self.machine.events.add_handler('init_phase_3',
                                        self._initialize)

    def _initialize(self):
        self.ball_locks = self.config['ball_locks']
        self.shoot_again = False
        self.enabled = False
        self.source_playfield = self.config['source_playfield']

    def start(self, **kwargs):
        if not self.enabled:
            return

        if self.balls_ejected > 0:
            self.log.debug("Cannot start MB because %s are still in play",
                           self.balls_ejected)

        self.shoot_again = True
        self.log.debug("Starting multiball with %s balls",
                       self.config['ball_count'])

        self.balls_ejected = self.config['ball_count'] - 1

        self.machine.game.add_balls_in_play(balls=self.balls_ejected)

        balls_added = 0

        # use lock_devices first
        for device in self.ball_locks:
            balls_added += device.release_balls(self.balls_ejected - balls_added)

            if self.balls_ejected - balls_added <= 0:
                break

        # request remaining balls
        if self.balls_ejected - balls_added > 0:
            self.source_playfield.add_ball(balls=self.balls_ejected - balls_added)

        if self.config['shoot_again'] == False:
            # No shoot again. Just stop multiball right away
            self.stop()
        else:
            # Enable shoot again
            self.machine.events.add_handler('ball_drain',
                                            self._ball_drain_shoot_again,
                                            priority=1000)
            # Register stop handler
            if not isinstance(self.config['shoot_again'], bool):
                self.delay.add('disable_shoot_again',
                               self.config['shoot_again'], self.stop)

        self.machine.events.post("multiball_" + self.name + "_started",
                         balls=self.config['ball_count'])

    def _ball_drain_shoot_again(self, balls, **kwargs):
        if balls <= 0:
            return {'balls': balls}

        self.machine.events.post("multiball_" + self.name + "_shoot_again", balls=balls)

        self.log.debug("Ball drained during MB. Requesting a new one")
        self.source_playfield.add_ball(balls=balls)
        return {'balls': 0}


    def _ball_drain_count_balls(self, balls, **kwargs):
        self.balls_ejected -= balls
        if self.balls_ejected <= 0:
            self.balls_ejected = 0
            self.machine.events.remove_handler(self._ball_drain_count_balls)
            self.machine.events.post("multiball_" + self.name + "_ended")
            self.log.debug("Ball drained. MB ended.")
        else:
            self.log.debug("Ball drained. %s balls remain until MB ends",
                           self.balls_ejected)

        # TODO: we are _not_ claiming the balls because we want it to drain.
        # However this may result in wrong results with multiple MBs at the
        # same time. May be we should claim and remove balls manually?

        return {'balls': balls}

    def stop(self, **kwargs):
        self.log.debug("Stopping shoot again of multiball")
        self.shoot_again = False

        # disable shoot again
        self.machine.events.remove_handler(self._ball_drain_shoot_again)

        # add handler for ball_drain until self.balls_ejected are drained
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_count_balls)

    def enable(self, **kwargs):
        """ Enables the multiball. If the multiball is not enabled, it cannot
        start.
        """
        self.log.debug("Enabling...")
        self.enabled = True

    def disable(self, **kwargs):
        """ Disabless the multiball. If the multiball is not enabled, it cannot
        start.
        """
        self.log.debug("Disabling...")
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the multiball and disables it.
        """
        self.enabled = False
        self.shoot_again = False
        self.balls_ejected = 0


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
