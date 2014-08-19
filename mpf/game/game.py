"""Contains the Game class which is the code that actually runs and manages an
actual game in a pinball machine.

Note that in the Mission Pinball Framework, a distinction is made between a
*game* and a *machine*. A *game* refers to a game in progress, whereas a
*machine* is the physical pinball machine.

"""
# game.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.machine_mode import MachineMode
from mpf.game.player import Player


class Game(MachineMode):
    """Base class that runs an active game on a pinball machine.

    Responsible for creating players, starting and ending balls, rotating to
    the next player, etc.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine):
        super(Game, self).__init__(machine)
        self.log = logging.getLogger("Game")

        # Intialize variables
        Player.total_players = 0
        self.player = None  # This is the current player
        self.player_list = []

        # todo register for request_to_start_game so you can deny it, or allow
        # it with a long press

        # todo if we don't wrap these handlers in this append thing, we're
        # screwed because they won't be removed. Should change this to a
        # decorator and maybe pull a local reference to the event manager
        # into this module so we can decorate just these things?
        # Then best practice is to use the local ref so it's properly
        # decorated?
        self.registered_event_handlers.append(self.machine.events.add_handler(
            'ball_add_live_success', self.ball_add_live_success))
        self.registered_event_handlers.append(self.machine.events.add_handler(
            'ball_remove_live', self.ball_remove_live))
        self.registered_event_handlers.append(self.machine.events.add_handler(
            'player_add_success', self.player_add_success))
        self.registered_event_handlers.append(self.machine.events.add_handler(
            'sw_start', self.request_player_add))

    def start(self):
        """Automatically called when the *Game* machine mode becomes active.

        """
        super(Game, self).start()
        self.log.info("Game Starting!!")
        # todo audit game start

        self.machine.events.post('game_starting', ev_type='queue',
                                 callback=self.game_started, game=self)

    def game_started(self, ev_result=True, game=None):
        """All the modules that needed to do something on game start are done,
        so our game is officially 'started'.
        """
        # we ignore game in the params since that was just a reference that
        # was passed around to other registered handlers, but we don't need
        # it here.

        self.request_player_add()  # if this fails we're in limbo.

    def player_add_success(self, player):
        """Called when a new player is successfully added to the current game
        (including when the first player is added).

        If this is the first player, calls :meth:`player_turn_start`.
        """
        if player.vars['number'] == 1:  # this is the first player
            self.player_turn_start()

    def tick(self):
        """Called once per machine tick.

        Currently this method does nothing. That probably won't be the case
        forever.

        """
        while self.active:
            # do something here
            yield

    """
      _____                       __ _
     / ____|                     / _| |
    | |  __  __ _ _ __ ___   ___| |_| | _____      __
    | | |_ |/ _` | '_ ` _ \ / _ \  _| |/ _ \ \ /\ / /
    | |__| | (_| | | | | | |  __/ | | | (_) \ V  V /
     \_____|\__,_|_| |_| |_|\___|_| |_|\___/ \_/\_/

    """

    def ball_starting(self):
        """Called when a new ball is starting.

        Note this method is called for each ball that starts, even if it's
        after a Shoot Again scenario for the same player.

        Posts a queue event called *ball_starting*, giving other modules the
        opportunity to do things before the ball actually starts. Once that
        event is clear, this method calls :meth:`ball_started`.
        """
        self.log.debug("ball_starting for Ball %s", self.player.vars['ball'])
        self.log.debug("***************************************************")
        self.log.debug("***************************************************")
        self.log.debug("**                                               **")
        self.log.debug("**    Player: %s    Ball: %s   Score: %s",
                       self.player.vars['number'], self.player.vars['ball'],
                       self.player.vars['score'])
        self.log.debug("**                                               **")
        self.log.debug("***************************************************")
        self.log.debug("***************************************************")
        self.machine.events.post('ball_starting', ev_type='queue',
                                 callback=self.ball_started)

    def ball_started(self, ev_result=True):
        """Called when the other modules have approved a ball start.

        Mainly used to enable the AutoFire coil rules, like enabling the
        flippers and bumpers.

        """
        if ev_result is False:
            return
            # todo what happens if this fails? I mean it shouldn't, but if
            # any ball_starting handler returns False, it will fail and we'll
            # be in limbo?
        self.log.debug("ball_started for Ball %s", self.player.vars['ball'])
        self.machine.enable_autofires()  # move to machine_controller
        self.machine.enable_flippers()

        # todo skillshot
        self.machine.events.post('ball_started')
        # todo post event to reset pf?

    def ball_ending(self):
        """Starts the ball ending process.

        This method posts the queue event *ball_ending*, giving other modules
        an opportunity to finish up whatever they need to do before the ball
        ends. Once all the registered handlers for that event have finished,
        this method calls :meth:`ball_ended`.

        Currently this method also disables the autofire coils and flippers,
        though that's temporary as we'll move those into config file options.
        """
        # todo check tilt

        # todo everything below is hard coded temporary
        self.machine.disable_autofires()
        self.machine.disable_flippers()

        self.machine.events.post('ball_ending', ev_type='queue',
                                 callback=self.ball_ended)

    def ball_ended(self, ev_result=True):
        """Called when the ball has successfully ended.

        This method is called after all the registered handlers of the queue
        event *ball_ended* finish. (So typically this means that animations
        have finished, etc.)

        This method also decides if the same player should shoot again (if
        there's an extra ball) or whether the machine controller should rotate
        to the next player. It will also end the game if all players and balls
        are done.

        """
        if ev_result is False:
            return
        # todo check extra balls
        # todo next_player()
        self.machine.events.post('ball_ended')
        # todo this could be a bug, because if the event queue is busy then
        # this event will get queued and the code will move on. The next part
        # of this code will rotate the player. What if it rotates to a new
        # player and we have some game ending stuff that tries to end the
        # current player, but it accidentally gets applied to the new player
        # since we rotated already?

        if self.player.vars['ball'] == self.machine.config['Game']\
                ['Balls per game'] and \
                self.player.vars['number'] == Player.total_players:
            self.game_ending()
        else:
            self.player_rotate()
            self.player_turn_start()

    def game_ending(self):
        """Called when the game decides it should end.

        This method posts the queue event *game_ending*, giving other modules
        an opportunity to finish up whatever they need to do before the game
        ends. Once all the registered handlers for that event have finished,
        this method calls :meth:`game_end`.

        """
        pass
        self.machine.events.post('game_ending', ev_type='queue',
                                 callback=self.game_end)

    def game_end(self, ev_result=True):
        """Actually ends the game once the *game_ending* event is clear.

        Eventually this method will do lots of things. For now it just
        advances the machine flow which ends the :class:`Game` mode and starts the
        :class:`Attract` mode.

        """
        if ev_result is False:
            return
        self.log.debug("game_end")
        # todo disable flippers
        # todo audit games played
        # todo audit game time
        # todo audit score
        # todo post game end event
        self.machine.events.post('machine_flow_advance')

    def shoot_again(self):
        """Called when the same player should shoot again."""
        pass

    def ball_saved(self):
        """Called when a ball is saved."""
        pass

    def ball_add_live_success(self):
        """Called after the ball controller has determined that a ball was
        successfully added to the game.

        This method increments the `num_balls_in_play` variable. If multiple
        balls have been added (like if a post drops that releases several
        balls), then call this method once for each ball.

        """
        pass

    def ball_remove_live(self):
        """Called when a ball in play has been removed from the playfield.

        This method decrements the `num_balls_in_play` variable. If that value
        drops below 1, it calls :meth:`ball_ending`.

        """
        if self.machine.ball_controller.num_balls_in_play < 1:
            # todo should we log if this is neg?
            self.ball_ending()

    """
    _____  _
   |  __ \| |
   | |__) | | __ _ _   _  ___ _ __
   |  ___/| |/ _` | | | |/ _ \ '__|
   | |    | | (_| | |_| |  __/ |
   |_|    |_|\__,_|\__, |\___|_|
                    __/ |
                   |___/
    """

    def request_player_add(self):
        """Called by any module that wants to add a player to an active game.

        This method contains the logic to verify whether it's ok to add a
        player. (For example, the game must be on ball 1 and the current
        number of players must be less than the max number allowed.)

        Assuming this method believes it's ok to add a player, it posts the
        boolean evet *player_add_request* to give other modules the opportunity
        to deny it. (For example, a credits module might deny the request if
        there are not enough credits in the machine.)

        If *player_add_request* comes back True, the event
        *player_add_success* is posted with a reference to the new player
        object as a *player* kwarg.

        """
        self.log.debug("Received request to add player.")

        # There area few things we have to check first. If this all passes,
        # then we'll raise the event to ask other modules if it's ok to add a
        # player

        if len(self.player_list) >= self.machine.config['Game']\
                ['Max players per game']:
            self.log.debug("Game is at max players. Cannot add another.")
            return False

        if self.player and self.player.vars['ball'] > 1:  # todo config setting
            self.log.debug("Current ball is after Ball 1. Cannot add player.")
            return False

        self.machine.events.post('player_add_request', ev_type='boolean',
                                 callback=self._player_add)

    def _player_add(self, ev_result=True):
        # This is the callback from our request player add event.
        # Don't call it directly.
        if ev_result is False:
            self.log.debug("Request to add player has been denied.")
        else:
            new_player = Player()
            self.player_list.append(new_player)
            self.machine.events.post('player_add_success', player=new_player)

    def player_turn_start(self):
        """Called at the beginning of a player's turn.

        Note this method is only called when a new player is first up. So if
        the same player shoots again due to an extra ball, this method is not
        called again.

        """

        # If we get a request to start a turn but we haven't done a rotate to
        # set the first player, do that now.
        if not self.player:
            self.player_rotate()

        self.player.vars['ball'] += 1
        self.machine.events.post('player_turn_start')
        self.ball_starting()  # todo is this ok to jump right into?
        # todo wonder if we should do player_turn_start as boolean? meh..

    def player_rotate(self, player_num=None):
        """Rotates the game to the next player.

        This method is called after a player's turn is over, so it's even used
        in single-player games between balls.

        All it does really is set :attr:`player` to the next player's number.

        Parameters
        ----------

        player_num : int
            Lets you specify which player you want to rotate to. If None, it
            just rotates to the next player in order.

        """
        # todo  do cool stuff in the future to change order, etc.

        if not self.player:
            self.player = self.player_list[0]
        else:

            if self.player.vars['number'] < Player.total_players:
                self.player = self.player_list[self.player.vars['number']]
                # Note the above line is kind of confusing but it works because
                # the current player number is always 1 more than the index.
                # i.e. "Player 1" has an index of 0, etc. So using the current
                # player number as the next player's index works out.
            else:
                self.player = self.player_list[0]
        self.log.info("Player rotate: Now up is Player %s",
                      self.player.vars['number'])



# player events should come next, including tracking inc/dec, other values

# sub mode(s)?
# tilted
# bonus

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
