"""Contains the Game class which is the Machine Mode that actually runs and
manages an the game in a pinball machine.

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
from mpf.system.timing import Timing


class Game(MachineMode):
    """Base class that runs an active game on a pinball machine.

    Responsible for creating players, starting and ending balls, rotating to
    the next player, etc.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine, name):
        super(Game, self).__init__(machine, name)
        self.log = logging.getLogger("Game")

        self.machine.game = None

    def start(self, buttons=None, hold_time=None):
        """Automatically called when the *Game* machine mode becomes active."""
        super(Game, self).start()
        self.log.info("Game Starting!!")

        if buttons:
            self.buttons_held_on_start = buttons
        if hold_time:
            self.start_button_hold_time = hold_time

        # Intialize variables
        Player.total_players = 0
        self.player = None  # This is the current player
        self.player_list = []
        self.machine.game = self

        self.num_balls_in_play = 0

        self.machine.tilted = False

        # Ball Save - todo might move these
        self.flag_ball_save_active = False
        self.flag_ball_save_multiple_saves = False
        self.flag_ball_save_paused = False
        self.timer_ball_save = 0

        # todo register for request_to_start_game so you can deny it, or allow
        # it with a long press

        self.registered_event_handlers.append(
            self.machine.events.add_handler('ball_add_live',
                                            self.ball_live_count_change))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('player_add_success',
                                            self.player_add_success))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('sw_start',
                                            self.request_player_add))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('ball_ended',
                                            self.ball_ended))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('game_ended',
                                            self.game_ended))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('tilt',
                                            self.tilt, priority=1000))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('slam_tilt',
                                            self.slam_tilt, priority=1000))

        if 'player_controlled_eject_tag' in self.machine.config['Game']:
            self.registered_event_handlers.append(
                self.machine.events.add_handler('sw_' +
                                                self.machine.config['Game']
                                                ['player_controlled_eject_tag'],
                                                self.player_eject_request))

        if ('Restart on long press' in self.machine.config['Game'] and
                self.machine.config['Game']['Restart on long press']):
            self.setup_midgame_restart()

        # Add our first player
        self.request_player_add()

        self.machine.events.post('game_starting', ev_type='queue',
                                 callback=self.game_started, game=self)

    def stop(self):
        self.machine.game = None
        super(Game, self).stop()

    def setup_midgame_restart(self, tag='start', time='1s', min_ball=0):
        """Allows a long button press to restart the game."""
        pass
        '''
        self.min_restart_ball = min_ball

        for switch in self.machine.switches.items_tagged(tag):
            self.registered_switch_handlers.append(
                self.machine.switch_controller.add_switch_handler(
                    switch_name=switch.name,
                    callback=self._midgame_restart_handler,
                    state=1,
                    ms=Timing.string_to_ms(time))
            )
        '''

    def _midgame_restart_handler(self, **kwargs):
        if self.player and self.player.vars['ball'] > self.min_restart_ball:
            self.log.debug("------Restarting game via long button press------")
            self.machine.flow_advance(1)

        # todo this should post the request to start game event first

    def game_started(self, ev_result=True, game=None):
        """All the modules that needed to do something on game start are done,
        so our game is officially 'started'.
        """
        self.log.debug("Entering Game.game_started")
        # we ignore game in the params since that was just a reference that
        # was passed around to other registered handlers, but we don't need
        # it here.
          # if this fails we're in limbo.
        self.machine.events.post('game_started')
        self.player_turn_start()

    def player_add_success(self, player, **kwargs):
        """Called when a new player is successfully added to the current game
        (including when the first player is added).

        If this is the first player, calls :meth:`player_turn_start`.
        """
        self.log.info("Player added successfully. Total players: %s",
                      Player.total_players)

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

        self.machine.tilted = False

        self.machine.events.post('ball_starting', ev_type='queue',
                                 callback=self.ball_started)

    def ball_started(self, ev_result=True):
        self.log.debug("Game Machine Mode ball_started()")
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

        # register handlers to watch for ball drain and live ball removed

        self.registered_event_handlers.append(
            self.machine.events.add_handler('ball_remove_live',
                                            self.ball_live_count_change))
        self.registered_event_handlers.append(
            self.machine.events.add_handler('ball_drain',
                                            self.ball_drained))

        # todo skillshot

        self.log.debug("Game is setting Balls in Play to 1")
        self.num_balls_in_play = 1

        self.machine.events.post('ball_started', ball=self.player.vars['ball'],
                                 player=self.player.vars['number'])

        self.machine.ball_controller.stage_ball('ball_add_live')

        # todo register for notification of ball added live?

    def player_eject_request(self):
        self.log.debug("Received player eject request")
        self.machine.ball_controller.add_live()
        # what happens if it can't and the player hits the button again? todo

    def ball_live_count_change(self):
        self.log.debug("Received ball live count change")
        # the number of live balls has changed
        pass

    def ball_drained(self, balls=0):
        self.log.debug("Entering Game.ball_drained()")

        if balls:
            self.log.debug("Processing %s newly-drained ball(s)", balls)
            self.log.debug("Previous balls in play: %s", self.num_balls_in_play)
            self.num_balls_in_play -= balls
            self.log.debug("Balls in play now: %s", self.num_balls_in_play)

            if self.num_balls_in_play < 0:
                # This should only happen if we find a lost ball. #todo
                self.num_balls_in_play = 0
                self.log.warning("Balls in play went negative. Resetting to 0")

            if not self.num_balls_in_play:
                self.ball_ending()

        return {'balls': balls}

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

        # remove the handlers that were looking for ball drain since they'll
        # be re-added on next ball start
        self.machine.events.remove_handler(self.ball_live_count_change)
        self.machine.events.remove_handler(self.ball_drained)

        # todo should clean up the above since they are removed from the
        # active list of handlers but not the registered_handlers list.
        # It doesn't really matter since the game ending can just remove them
        # all, but technically it's not clean.

        # todo everything below is hard coded temporary

        self.num_balls_in_play = 0  # todo redundant?
        self.log.debug("Entering Game.ball_ending()")

        self.machine.events.post('ball_ending', ev_type='queue',
                                 callback=self._ball_ending_done)

    def _ball_ending_done(self, **kwargs):
        # Callback for when the ball_ending queue is clear. All this does is
        # post ball_ended, but we do it this way so that ball_ended slots in
        # properly after other existing events have been posted.
        self.machine.events.post('ball_ended')

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
        self.log.debug("Entering Game.ball_ended()")
        if ev_result is False:
            return

        if self.player.vars['extra_balls']:
            self.shoot_again()
            return

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
        self.log.debug("Entering Game.game_ending()")
        self.machine.events.post('game_ending', ev_type='queue',
                                 callback=self._game_ending_done)

    def _game_ending_done(self, **kwargs):
        # Callback for when the game_ending queue is clear. All this does is
        # post game_ended, but we do it this way so that game_ended slots in
        # properly after other existing events have been posted.
        self.machine.events.post('game_ended')

    def game_ended(self, **kwargs):
        """Actually ends the game once the *game_ending* event is clear.

        Eventually this method will do lots of things. For now it just
        advances the machine flow which ends the :class:`Game` mode and starts the
        :class:`Attract` mode.

        """
        self.log.debug("Entering Game.game_ended()")
        self.machine.events.post('machineflow_advance')

    def award_extra_ball(self, num=1, force=False):
        """Awards the player an extra ball.

        Args:
            num: Integer of the  number of extra balls to award. Default is 1.
            force: Boolean which allows you to force the extra ball even if it
                means the player would go above the max extra balls specified
                in the config files. Default is False.

        TODO: The limit checking is not yet implemented
        """
        self.log.debug("Entering Game.award_extra_ball()")
        self.player.vars['extra_balls'] += num
        self.machine.events.post('extra_ball_awarded')
        # todo add the limit checking

    def shoot_again(self):
        """Called when the same player should shoot again."""
        self.log.debug("Player %s Shoot Again", self.player.vars['index'] + 1)
        if self.player.vars['extra_balls'] > 0:
            self.player.vars['extra_balls'] -= 1
        self.ball_starting()

    def ball_saved(self):
        """Called when a ball is saved."""
        pass

    def tilt(self):
        """Called when the 'tilt' event is posted indicated the ball has tilted.
        """

        # todo add support to catch if the player tilts during ball ending?

        self.log.debug("Processing Ball Tilt")
        self.machine.tilted = True

        self.machine.ball_controller.set_live_count(0)
        self.num_balls_in_play = 0

        self.machine.events.add_handler('ball_ending',
                                        self._tilt_ball_ending_wait)

        self.ball_ending()

    def _tilt_ball_ending_wait(self, queue):
        # Method that hooks ball_ending which happens from a tilt. Used so we
        # can wait for the balls to drain before allowing the game to move on.

        self.machine.events.add_handler('tilted_ball_drain',
                                        self._tilt_ball_ending_clear)

        self.tilt_ball_ending_queue = queue
        self.tilt_ball_ending_queue.wait()

    def _tilt_ball_ending_clear(self, **kwargs):

        # If there are still live balls out there, wait for them to drain too.
        if self.machine.ball_controller.num_balls_live:
            return

        # todo there's a bug here. If there are multiple balls live when the
        # tilt occurs and one of the balls enters a device at the same time
        # another drains, in that instant there will technically be no balls
        # live and this queue will be cleared, though really it should wait
        # to see if another ball will be ejected to be drained.

        # Potential solution is to have ball devices check tilt status when
        # they find new balls, and if so to just eject them without posting
        # the ball_enter events.

        self.tilt_ball_ending_queue.clear()
        self.tilt_ball_ending_queue = None

        self.machine.events.remove_handler(self._tilt_ball_ending_wait)
        self.machine.events.remove_handler(self._tilt_ball_ending_clear)

    def slam_tilt(self):
        self.game_ended()

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
        boolean event *player_add_request* to give other modules the opportunity
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
            self.machine.events.post('player_add_success', player=new_player,
                                     num=new_player.vars['number'])

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

        self.machine.events.post('player_turn_start')

        self.player.vars['ball'] += 1
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

        if not self.player:  # no current player, grab the first one
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
        self.log.debug("Player rotate: Now up is Player %s",
                       self.player.vars['number'])



# player events should come next, including tracking inc/dec, other values

# sub mode(s)?
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
