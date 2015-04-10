"""Contains the Player class which reprsents a player in a pinball game.

"""
# player.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging


class Player(object):
    """ Base class for a player. One instance of this class is created for each
    player.

    The Game class maintains a "player" attribute which always points to the
    current player. You can access this via game.player. (Or
    self.machine.game.player).

    This class is responsible for tracking per-player variables. There are
    several ways they can be used:

    player.ball = 0 (sets the player's 'ball' value to 0)
    print player.ball (prints the value of the player's 'ball' value)

    If the value of a variable is requested but that variable doesn't exist,
    that variable will automatically be created (and returned) with a value of
    0.

    Every time a player variable is changed, an MPF is posted with the name
    "player_<name>". That event will have three parameters posted along with it:

    * value (the new value)
    * prev_value (the old value before it was updated)
    * change (the change in the value)

    For the 'change' parameter, it will attempt to subtract the old value from
    the new value. If that works, it will return the result as the change. If it
    doesn't work (like if you're not storing numbers in this variable), then
    the change paramter will be True if the new value is different and False if
    the value didn't change.

    Some examples:

    player.score = 0

    Event posted:
    'player_score' with Args: value=0, change=0, prev_value=0

    player.score += 500

    Event posted:
    'player_score' with Args: value=500, change=500, prev_value=0

    player.score = 1200

    Event posted:
    'player_score' with Args: value=1200, change=700, prev_value=500

    """

    total_players = 0  # might not use this here
    """Tracks the the number of players in the game (starting with 1)."""

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track player variable changes.
    """

    def __getattr__(self, name):
        if name in self.vars:
            return self.vars[name]
        else:
            self.vars[name] = 0
            return 0

    def __setattr__(self, name, value):
        prev_value = 0
        if name in self.vars:
            prev_value = self.vars[name]
        self.vars[name] = value

        try:
            change = value-prev_value
        except TypeError:
            if prev_value != value:
                change = True
            else:
                change = False

        if change:

            self.log.debug("Setting '%s' to: %s, (prior: %s, change: %s)",
                           name, self.vars[name], prev_value, change)
            self.machine.events.post('player_' + name,
                                     value=self.vars[name],
                                     prev_value=prev_value,
                                     change=change)

        if Player.monitor_enabled:
            for callback in self.machine.monitors['player']:
                callback(name=name, value=self.vars[name],
                         prev_value=prev_value, change=change)

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __setitem__(self, name, value):
        self.__setattr__(name, value)

    def __iter__(self):
        for name, value in self.vars.iteritems():
            yield name, value

    def __init__(self, machine):
        """Player object contructor:

        Args:
            machine: Machine controller
        """
        # use self.__dict__ below since __setattr__ would make these player vars
        self.__dict__['log'] = logging.getLogger("Player")
        self.__dict__['machine'] = machine
        self.__dict__['vars'] = dict()

        Player.total_players += 1

        # initialize player vars
        self.vars['index'] = Player.total_players - 1
        self.vars['number'] = Player.total_players

        self.log.debug("Creating new player: Player %s. (player index '%s')",
                      self.vars['number'], self.index)

    # todo method to dump the player vars to disk?

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
