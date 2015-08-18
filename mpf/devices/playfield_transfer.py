""" Transfer a ball between two playfields. E.g. lower to upper playfield via a ramp"""
# playfield_transfer.py
# Mission Pinball Framework
# MPF is written by Brian Madden & Gabe Knuth
# This module originally created by Jan Kantert
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.device import Device


class PlayfieldTransfer(Device):

    config_section = 'playfield_transfer'
    collection = 'playfield_transfer'
    class_label = 'playfield_transfer'

    def __init__(self, machine, name, config, collection=None):
        super(PlayfieldTransfer, self).__init__(machine, name, config,
                                                collection)

        self.machine.switch_controller.add_switch_handler(
            switch_name=self.config['ball_switch'].name,
            callback=self._ball_went_through,
            state=1, ms=0)

        # load target playfield
        self.target = self.config['eject_target']
        self.source = self.config['captures_from']

    def _ball_went_through(self):
        self.log.debug("Ball went from %s to %s", self.source.name,
                       self.target.name)

        # source playfield is obviously active
        # we will continue using a callback to keep the ball count sane
        # (otherwise it may go to -1 during the next event)
        self.machine.events.post('sw_' + self.source.name + '_active',
                                 callback=self._ball_went_through2)

    # used as callback in _ball_went_through
    def _ball_went_through2(self):
        # trigger remove ball from source playfield
        self.machine.events.post('balldevice_captured_from_' + self.source.name,
                                        balls=1)

        # inform target playfield about incomming ball
        self.machine.events.post('balldevice_' + self.name + '_ball_eject_attempt',
                                        balls=1,
                                        target=self.target,
                                        timeout=0,
                                        callback=self._ball_went_through3)

    # used as callback in _ball_went_through2
    def _ball_went_through3(self, balls, target, timeout):
        # promise (and hope) that it actually goes there
        self.machine.events.post('balldevice_' + self.name + '_ball_eject_success',
                                        balls=1,
                                        target=self.target,
                                        callback=self._ball_went_through4)

    # used as callback in _ball_went_through3
    def _ball_went_through4(self, balls, target):
        # since we confirmed eject target playfield has to be active
        self.machine.events.post('sw_' + self.target.name + '_active')


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
