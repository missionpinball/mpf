"""Contains the Player class which reprsents a player in a pinball game.

"""
# player.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging


class Player(object):
    """ Base class for a player in a pinball game. One instance of this class
    type is created for each player.

    This class is responsible for tracking per-player variables via a
    dictionary called :attr:`vars`. Several defaults are provided which the
    framework uses,  and you can extend it on your own.

    """

    total_players = 0  # might not use this here
    """Tracks the the number of players in the game (starting with 1)."""

    def __init__(self):
        """ Creates a new player object. Doesn't take an parameters.

        """
        self.log = logging.getLogger("Player")
        self.vars = {}  # todo default dic?
        self.index = Player.total_players  # player index starting with 0

        Player.total_players += 1

        # initialize player vars
        self.vars['ball'] = 0
        self.vars['score'] = 0
        self.vars['index'] = 0  # the player index (starts with 0)
        self.vars['number'] = Player.total_players

        self.log.info("Creating new player: Player %s. (player index '%s')",
                      self.vars['number'], self.index)

    # todo method to dump the player vars to disk?

    # todo nice methods to read or update player vars?

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
