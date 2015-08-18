"""Device that implements a ball save."""
# ball_save.py
# Mission Pinball Framework
# MPF is written by Brian Madden & Gabe Knuth
# This module originally written by Jan Kantert
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


from mpf.system.device import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.config import Config

class BallSave(Device):

    config_section = 'ball_saves'
    collection = 'ball_saves'
    class_label = 'ball_save'

    def __init__(self, machine, name, config, collection=None):
        super(BallSave, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        self.source_playfield = self.config['source_playfield']

    def enable(self, **kwargs):
        self.log.debug("Enabling...")

        # Enable shoot again
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_shoot_again,
                                        priority=1000)

        if self.config['auto_disable_time'] > 0:
            self.delay.add('disable_shoot_again',
                           self.config['auto_disable_time'], self.disable)

        self.machine.events.post('ball_save_' + self.name + '_enabled')

    def disable(self, **kwargs):
        self.log.debug("Disabling...")
        self.machine.events.remove_handler(self._ball_drain_shoot_again)
        self.delay.remove('disable_shoot_again')

        self.machine.events.post('ball_save_' + self.name + '_disabled')

    def _ball_drain_shoot_again(self, balls, **kwargs):
        if balls <= 0:
            return {'balls': balls}

        self.machine.events.post("ball_save_" + self.name + "_shoot_again", balls=balls)

        self.log.debug("Ball drained during ball save. Requesting a new one.")
        self.source_playfield.add_ball(balls=balls)
        return {'balls': 0}


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
