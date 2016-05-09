"""Contains the Game class which is the Machine Mode that actually runs and
manages an the game in a pinball machine.

Note that in the Mission Pinball Framework, a distinction is made between a
*game* and a *machine*. A *game* refers to a game in progress, whereas a
*machine* is the physical pinball machine.

"""

from mpf.core.mode import Mode
from mpf.core.player import Player


class Game(Mode):
    """Base mode that runs an active game on a pinball machine.

    Responsible for creating players, starting and ending balls, rotating to
    the next player, etc.

    """

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self._balls_in_play = 0
        self.player_list = list()
        self.machine.game = None
        self.tilted = False
        self.slam_tilted = False
        self.player = None
        self.buttons_held_on_start = None
        self.start_button_hold_time = None
        self.num_players = None

    @property
    def balls_in_play(self):
        return self._balls_in_play

    @balls_in_play.setter
    def balls_in_play(self, value):
        prev_balls_in_play = self._balls_in_play

        if value > self.machine.ball_controller.num_balls_known:
            self._balls_in_play = self.machine.ball_controller.num_balls_known

        elif value < 0:
            self._balls_in_play = 0

        else:
            self._balls_in_play = value

        self.log.debug("Balls in Play change. New value: %s, (Previous: %s)",
                       self._balls_in_play, prev_balls_in_play)

        if self._balls_in_play > 0:
            self.machine.events.post('balls_in_play',
                                     balls=self._balls_in_play)

        if prev_balls_in_play and not self._balls_in_play:
            self.ball_ending()

    def mode_start(self, buttons=None, hold_time=None, **kwargs):
        """Automatically called when the *Game* machine mode becomes active."""

        if buttons:
            self.buttons_held_on_start = buttons
        if hold_time:
            self.start_button_hold_time = hold_time

        # Intialize variables
        self.num_players = 0
        self.player = None
        self.player_list = list()
        self.machine.game = self
        self.tilted = False
        self.slam_tilted = False
        self._balls_in_play = 0

        # todo register for request_to_start_game so you can deny it, or allow
        # it with a long press

        self.add_mode_event_handler('player_add_success',
                                    self.player_add_success)

        if self.machine.config['game']['add_player_switch_tag']:
            self.add_mode_event_handler(
                self.machine.config['mpf']['switch_tag_event'].replace(
                    '%', self.machine.config['game']['add_player_switch_tag']),
                self.request_player_add)

        self.add_mode_event_handler('ball_ended', self.ball_ended)
        self.add_mode_event_handler('game_ended', self.game_ended)

        self.machine.events.post('enable_volume_keys')

        self.machine.events.post_queue('game_starting',
                                       callback=self.game_started, game=self)

    def mode_stop(self, **kwargs):
        self.machine.game = None

    def game_started(self, ev_result=True, **kwargs):
        """All the modules that needed to do something on game start are done,
        so our game is officially 'started'.

        """

        del kwargs

        if ev_result:
            self.machine.remove_machine_var_search(startswith='player',
                                                   endswith='_score')

            if not self.player_list:
                # Sometimes game_starting handlers will add players, so we only
                # have to here if there aren't any players yet.
                self._player_add()

            self.machine.events.post('game_started')

            self.player_turn_start()

        else:  # something canceled the game start
            self.game_ending()

    def player_add_success(self, player, **kwargs):
        """Called when a new player is successfully added to the current game
        (including when the first player is added).

        """
        del player
        del kwargs
        self.log.info("Player added successfully. Total players: %s",
                      self.num_players)

        if self.num_players == 2:
            self.machine.events.post('multiplayer_game')

    def ball_starting(self):
        """Called when a new ball is starting.

        Note this method is called for each ball that starts, even if it's
        after a Shoot Again scenario for the same player.

        Posts a queue event called *ball_starting*, giving other modules the
        opportunity to do things before the ball actually starts. Once that
        event is clear, this method calls :meth:`ball_started`.
        """
        self.log.info("***************************************************")
        self.log.info("****************** BALL STARTING ******************")
        self.log.info("**                                               **")
        self.log.info("**    Player: {}    Ball: {}   Score: {}".format(
                      self.player.number, self.player.ball,
                      self.player.score).ljust(49) + '**')
        self.log.info("**                                               **")
        self.log.info("***************************************************")
        self.log.info("***************************************************")

        self.machine.events.post_queue('ball_starting',
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
        self.log.debug("ball_started for Ball %s", self.player.ball)

        # register handlers to watch for ball drain and live ball removed

        self.add_mode_event_handler('ball_drain', self.ball_drained)

        self.balls_in_play = 1

        self.machine.events.post('ball_started', ball=self.player.ball,
                                 player=self.player.number)

        if self.num_players == 1:
            self.machine.events.post('single_player_ball_started')
        else:
            self.machine.events.post('multi_player_ball_started')
            self.machine.events.post(
                'player_{}_ball_started'.format(self.player.number))

        self.machine.playfield.add_ball(player_controlled=True)

    def ball_drained(self, balls=0, **kwargs):
        del kwargs
        self.log.debug("Entering Game.ball_drained()")

        if balls:
            self.log.debug("Processing %s newly-drained ball(s)", balls)
            self.balls_in_play -= balls

        return {'balls': balls}

    def ball_ending(self):
        """Starts the ball ending process.

        This method posts the queue event *ball_ending*, giving other modules
        an opportunity to finish up whatever they need to do before the ball
        ends. Once all the registered handlers for that event have finished,
        this method calls :meth:`ball_ended`.

        Currently this method also disables the autofire_coils and flippers,
        though that's temporary as we'll move those into config file options.
        """

        # remove the handlers that were looking for ball drain since they'll
        # be re-added on next ball start
        self.machine.events.remove_handler(self.ball_drained)

        # todo should clean up the above since they are removed from the
        # active list of handlers but not the registered_handlers list.
        # It doesn't really matter since the game ending can just remove them
        # all, but technically it's not clean.

        self._balls_in_play = 0

        # todo everything below is hard coded temporary

        self.log.debug("Entering Game.ball_ending()")

        self.machine.events.post_queue('ball_ending',
                                       callback=self._ball_ending_done)

    def _ball_ending_done(self, **kwargs):
        # Callback for when the ball_ending queue is clear. All this does is
        # post ball_ended, but we do it this way so that ball_ended slots in
        # properly after other existing events have been posted.
        del kwargs
        self.machine.events.post('ball_ended')

    def ball_ended(self, ev_result=True, **kwargs):
        """Called when the ball has successfully ended.

        This method is called after all the registered handlers of the queue
        event *ball_ended* finish. (So typically this means that animations
        have finished, etc.)

        This method also decides if the same player should shoot again (if
        there's an extra ball) or whether the machine controller should rotate
        to the next player. It will also end the game if all players and balls
        are done.

        """
        del kwargs
        self.log.debug("Entering Game.ball_ended()")
        if ev_result is False:
            return

        if self.slam_tilted:
            self.game_ending()
            return

        if self.player.extra_balls:
            self.award_extra_ball()
            return

        if (self.player.ball ==
                self.machine.config['game']['balls_per_game'] and
                self.player.number == self.num_players):
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
        self.machine.events.post_queue('game_ending',
                                       callback=self._game_ending_done)

    def _game_ending_done(self, **kwargs):
        # Callback for when the game_ending queue is clear. All this does is
        # post game_ended, but we do it this way so that game_ended slots in
        # properly after other existing events have been posted.
        del kwargs
        self.player_turn_stop()
        self.machine.events.post('game_ended')

    def game_ended(self, **kwargs):
        """Actually ends the game once the *game_ending* event is clear.

        Eventually this method will do lots of things. For now it just
        advances the machine flow which ends the :class:`Game` mode and starts the
        :class:`Attract` mode.

        """
        del kwargs
        self.log.debug("Entering Game.game_ended()")

    def award_extra_ball(self):
        """Called when the same player should shoot again."""
        self.log.debug("Awarded extra ball to Player %s. Shoot Again", self.player.index + 1)
        self.player.extra_balls -= 1
        self.ball_starting()

    def request_player_add(self, **kwargs):
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
        del kwargs
        self.log.debug("Received request to add player.")

        # There area few things we have to check first. If this all passes,
        # then we'll raise the event to ask other modules if it's ok to add a
        # player

        if len(self.player_list) >= self.machine.config['game']['max_players']:
            self.log.debug("Game is at max players. Cannot add another.")
            return False

        if self.player and self.player.ball > 1:  # todo config setting
            self.log.debug("Current ball is after Ball 1. Cannot add player.")
            return False

        return self.machine.events.post_boolean('player_add_request',
                                                callback=self._player_add)

    def _player_add(self, ev_result=True):
        # This is the callback from our request player add event.
        # Don't call it directly.

        if ev_result is False:
            self.log.debug("Request to add player has been denied.")
            return False
        else:
            player = Player(self.machine, self.player_list)
            self.num_players = len(self.player_list)

            self.machine.create_machine_var(
                name='player{}_score'.format(player.number),
                value=player.score,
                persist=True)

            return player

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

        self.machine.events.post('player_turn_start', player=self.player,
                                 number=self.player.number,
                                 callback=self._player_turn_started)

    def player_turn_stop(self):

        if not self.player:
            return

        self.machine.events.post('player_turn_stop', player=self.player,
                                 number=self.player.number)

        self.machine.set_machine_var(
            name='player{}_score'.format(self.player.number),
            value=self.player.score)

        if self.player.number < self.num_players:
            self.player = self.player_list[self.player.number]
            # Note the above line is kind of confusing but it works because
            # the current player number is always 1 more than the index.
            # i.e. "Player 1" has an index of 0, etc. So using the current
            # player number as the next player's index works out.
        else:
            self.player = self.player_list[0]

    def _player_turn_started(self, **kwargs):
        del kwargs
        self.player.ball += 1
        self.ball_starting()

    def player_rotate(self):
        """Rotates the game to the next player.

        This method is called after a player's turn is over, so it's even used
        in single-player games between balls.

        All it does really is set :attr:`player` to the next player's number.

        Args:
        """
        # todo  do cool stuff in the future to change order, etc.

        if self.player:
            self.player_turn_stop()

        else:  # no current player, grab the first one
            self.player = self.player_list[0]

        self.log.debug("Player rotate: Now up is Player %s",
                       self.player.number)

# todo player events should come next, including tracking inc/dec, other values
