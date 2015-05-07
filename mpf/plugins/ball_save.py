"""MPF plugin for a ball saver code which is used to give the player another
ball if their first ball drains too fast.

This plugin is not yet finished and doesn't work yet.

"""
# ball_save.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


class BallSave(object):
    """Base class which implements a ball saver instance. You can use this
    as-is, enhance it, or replace it altogether.
    """

    def __init__(self, game):
        self.game = game
        self.active = False

        # register for events
        # ball_drain
        # timers_pause
        # timers_resume

    def enable(self, time=None, balls=None):
        pass

    def ball_drain(self, balls):
        # This code is not yet implemented

        self.log.debug("ball save active: %s", self.flag_ball_save_active)
        self.log.debug("num balls to save: %s", self.num_balls_to_save)

        if self.balls_in_play:  # if there was at least one BIP
            if self.flag_ball_save_active:  # if ball save is active
                # nope, should post event saying we got one, then let
                # other modes potentially kick in? Do a boolean event?
                self.log.debug("Ball save is active")
                if self.num_balls_to_save == -1:  # save all the new balls
                    self.log.debug("We drained %s new balls and"
                                     " will save all of them",
                                     new_balls)
                    while new_balls > 0:
                        self.save_ball()
                        new_balls -= 1
                else:  # save the balls but count down as we do
                    self.log.debug("We drained %s new balls and will save %s "
                                   "of them", new_balls,
                                   self.num_balls_to_save)
                    while self.num_balls_to_save > 0 and new_balls > 0:
                        self.save_ball()
                        new_balls -= 1
                        self.num_balls_to_save -= 1

        return {'balls': balls}


plugin_class = BallSave


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
