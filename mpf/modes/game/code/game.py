"""Contains the Game class which is the Machine Mode that actually runs and manages an the game in a pinball machine.

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
        """Initialise game."""
        super().__init__(machine, config, name, path)
        self._balls_in_play = 0
        self.player_list = list()
        self.machine.game = None
        self.slam_tilted = False
        self.tilted = False
        self.player = None
        self.num_players = None
        self.balls_per_game = None

    @property
    def balls_in_play(self):
        """Return balls in play."""
        return self._balls_in_play

    @balls_in_play.setter
    def balls_in_play(self, value):
        """Set balls in play."""
        prev_balls_in_play = self._balls_in_play

        if value > self.machine.ball_controller.num_balls_known:
            self._balls_in_play = self.machine.ball_controller.num_balls_known

        elif value < 0:
            self._balls_in_play = 0

        else:
            self._balls_in_play = value

        self.debug_log("Balls in Play change. New value: %s, (Previous: %s)",
                       self._balls_in_play, prev_balls_in_play)

        if self._balls_in_play > 0:
            self.machine.events.post('balls_in_play',
                                     balls=self._balls_in_play)
            '''event: balls_in_play
            desc: The number of balls in play has just changed, and there is at
            least 1 ball in play.

            Note that the number of balls in play is not necessarily the same
            as the number of balls loose on the playfield. For example, if the
            player shoots a lock and is watching a cut scene, there is still
            one ball in play even though there are no balls on the playfield.

            args:
            balls: The number of ball(s) in play.'''

        if prev_balls_in_play and not self._balls_in_play:
            self.ball_ending()

    def mode_start(self, buttons=None, hold_time=None, **kwargs):
        """Automatically called when the *Game* machine mode becomes active."""
        del hold_time
        del buttons

        # Intialize variables
        self.num_players = 0
        self.player = None
        self.player_list = list()
        self.machine.game = self
        self.slam_tilted = False
        self.tilted = False
        self._balls_in_play = 0
        self.balls_per_game = self.machine.config['game']['balls_per_game'].evaluate([])

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

        self.machine.events.post_queue('game_starting',
                                       callback=self.game_started, game=self)
        '''event: game_starting
        desc: A game is in the process of starting. This is a queue event, and
        the game won't actually start until the queue is cleared.

        args:
        game: A reference to the game mode object.
        '''

    def mode_stop(self, **kwargs):
        """Stop mode."""
        for mode in self.machine.modes:
            if mode.active and not mode.stopping and mode.config['mode']['game_mode']:
                raise AssertionError("Mode {} is not supposed to run outside of game.".format(mode.name))
        self.machine.game = None

    def game_started(self, ev_result=True, **kwargs):
        """All the modules that needed to do something on game start are done, so our game is officially 'started'."""
        del kwargs

        if ev_result:
            if not self.player_list:
                # Sometimes game_starting handlers will add players, so we only
                # have to here if there aren't any players yet.
                self._player_add()

            # set up first player
            self.player = self.player_list[0]

            self.player_turn_start()

            self.machine.events.post('game_started')
            '''event: game_started
            desc: A new game has started.'''

        else:  # something canceled the game start
            self.game_ending()

    def player_add_success(self, player, **kwargs):
        """Called when a new player is successfully added to the current game.

        This includes when the first player is added.
        """
        del player
        del kwargs
        self.info_log("Player added successfully. Total players: %s",
                      self.num_players)

        if self.num_players == 2:
            self.machine.events.post('multiplayer_game')
            '''event: multiplayer_game
            desc: A second player has just been added to this game, meaning
            this is now a multiplayer game.

            This event is typically used to switch the score display from the
            single player layout to the multiplayer layout.'''

    def ball_starting(self, is_extra_ball=False):
        """Called when a new ball is starting.

        Note this method is called for each ball that starts, even if it's
        after a Shoot Again scenario for the same player.

        Posts a queue event called *ball_starting*, giving other modules the
        opportunity to do things before the ball actually starts. Once that
        event is clear, this method calls :meth:`ball_started`.
        """
        self.debug_log("***************************************************")
        self.debug_log("****************** BALL STARTING ******************")
        self.debug_log("**                                               **")
        self.debug_log("**    Player: {}    Ball: {}   Score: {}".format(
                       self.player.number, self.player.ball,
                       self.player.score).ljust(49) + '**')
        self.debug_log("**                                               **")
        self.debug_log("***************************************************")
        self.debug_log("***************************************************")

        self.machine.events.post_queue('ball_starting',
                                       balls_remaining=self.balls_per_game- self.player.ball,
                                       is_extra_ball=is_extra_ball,
                                       callback=self.ball_started)
        '''event: ball_starting
        desc: A ball is starting. This is a queue event, so the ball won't
        actually start until the queue is cleared.'''

    def ball_started(self, ev_result=True, **kwargs):
        """Ball started."""
        del kwargs
        self.debug_log("Game Machine Mode ball_started()")
        """Called when the other modules have approved a ball start.

        Mainly used to enable the AutoFire coil rules, like enabling the
        flippers and bumpers.
        """
        if ev_result is False:
            return
            # todo what happens if this fails? I mean it shouldn't, but if
            # any ball_starting handler returns False, it will fail and we'll
            # be in limbo?
        self.debug_log("ball_started for Ball %s", self.player.ball)

        # register handlers to watch for ball drain and live ball removed

        self.add_mode_event_handler('ball_drain', self.ball_drained)

        self.balls_in_play = 1

        self.machine.events.post('ball_started', ball=self.player.ball,
                                 player=self.player.number)
        '''event: ball_started
        desc: A new ball has started.
        args:
        ball: The ball number.
        player: The player number.'''

        if self.num_players == 1:
            self.machine.events.post('single_player_ball_started')
            '''event: single_player_ball_started
            desc: A new ball has started, and this is a single player game.'''
        else:
            self.machine.events.post('multi_player_ball_started')
            '''event: multi_player_ball_started
            desc: A new ball has started, and this is a multiplayer game.'''
            self.machine.events.post(
                'player_{}_ball_started'.format(self.player.number))
            '''event player_(number)_ball_started
            desc: A new ball has started, and this is a multiplayer game.
            The player number is the (number) in the event that's posted.'''

        self.machine.playfield.add_ball(player_controlled=True)

    def ball_drained(self, balls=0, **kwargs):
        """Ball drained."""
        del kwargs
        self.debug_log("Entering Game.ball_drained()")

        if balls:
            self.debug_log("Processing %s newly-drained ball(s)", balls)
            self.balls_in_play -= balls

        return {'balls': balls}

    def ball_ending(self):
        """Start the ball ending process.

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

        self.debug_log("Entering Game.ball_ending()")
        self.machine.events.post('ball_will_end')
        '''event: ball_will_end
        desc: The ball is about to end. This event is posted just before
        :doc:`ball_ending`.'''

        self.machine.events.post_queue('ball_ending',
                                       callback=self._ball_ending_done)
        '''event: ball_ending
        desc: The ball is ending. This is a queue event and the ball won't
        actually end until the queue is cleared.

        This event is posted just after :doc:`ball_will_end`'''

    def _ball_ending_done(self, **kwargs):
        # Callback for when the ball_ending queue is clear. All this does is
        # post ball_ended, but we do it this way so that ball_ended slots in
        # properly after other existing events have been posted.
        del kwargs
        self.machine.events.post('ball_ended')
        '''event: ball_ended
        desc: The ball has ended.

        Note that this does not necessarily mean that the next player's turn
        will start, as this player may have an extra ball which means they'll
        shoot again.'''

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
        self.debug_log("Entering Game.ball_ended()")
        if ev_result is False:
            return

        if self.slam_tilted:
            self.game_ending()
            return

        if self.player.extra_balls:
            self.award_extra_ball()
            return

        if (self.player.ball >= self.balls_per_game and self.player.number == self.num_players):
            self.game_ending()
        else:
            self.player_rotate()

    def game_ending(self):
        """Called when the game decides it should end.

        This method posts the queue event *game_ending*, giving other modules
        an opportunity to finish up whatever they need to do before the game
        ends. Once all the registered handlers for that event have finished,
        this method calls :meth:`game_end`.

        """
        self.machine.events.post_queue('player_turn_ending', player=self.player,
                                       number=self.player.number,
                                       callback=self._game_ending2)

    def _game_ending2(self, **kwargs):
        del kwargs
        self.debug_log("Entering Game.game_ending()")
        self.machine.events.post_queue('game_ending',
                                       callback=self._game_ending_done)
        '''event: game_ending
        desc: The game is in the process of ending. This is a queue event, and
        the game won't actually end until the queue is cleared.'''

    def _game_ending_done(self, **kwargs):
        # Callback for when the game_ending queue is clear. All this does is
        # post game_ended, but we do it this way so that game_ended slots in
        # properly after other existing events have been posted.
        del kwargs
        self.player_turn_stop()     # this is out of order for legacy reasons in 0.33. fixed in 0.50
        self.machine.events.post('game_ended')
        '''event: game_ended
        desc: The game has ended.'''

    def game_ended(self, **kwargs):
        """Actually ends the game once the *game_ending* event is clear.

        Eventually this method will do lots of things. For now it just
        advances the machine flow which ends the :class:`Game` mode and starts the
        :class:`Attract` mode.

        """
        del kwargs
        self.debug_log("Entering Game.game_ended()")

        if not self.player_list:
            return

        for player in self.player_list:
            self.machine.create_machine_var(
                name='player{}_score'.format(player.number),
                value=player.score,
                persist=True)
            '''machine_var: player(x)_score

            desc: Holds the numeric value of a player's score. The "x" is the
            player number, so this actual machine variable is
            ``player1_score`` or ``player2_score``.

            Since these are machine variables, they are maintained even after
            a game is over. Therefore you can use these machine variables in
            your attract mode display show to show the scores of the last game
            that was played.

            These machine variables are updated at the end of each player's
            turn, and they persist on disk so they are restored the next time
            MPF starts up.

            '''

        # remove all other vars
        for i in range(len(self.player_list) + 1, self.machine.config['game']['max_players'].evaluate([])):
            self.machine.remove_machine_var('player{}_score'.format(i))

    def award_extra_ball(self):
        """Called when the same player should shoot again."""
        self.debug_log("Awarded extra ball to Player %s. Shoot Again", self.player.index + 1)
        self.player.extra_balls -= 1
        self.ball_starting(is_extra_ball=True)

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
        self.debug_log("Received request to add player.")

        # There area few things we have to check first. If this all passes,
        # then we'll raise the event to ask other modules if it's ok to add a
        # player

        if len(self.player_list) >= self.machine.config['game']['max_players'].evaluate([]):
            self.debug_log("Game is at max players. Cannot add another.")
            return False

        if self.player and self.player.ball > 1:  # todo config setting
            self.debug_log("Current ball is after Ball 1. Cannot add player.")
            return False

        result = self.machine.events.post_boolean('player_add_request',
                                                  callback=self._player_add)
        '''event: player_add_request
        desc: Posted to request that an additional player be added to this
        game. Any registered handler can deny the player add request by
        returning *False* to this event.
        '''
        return result

    def _player_add(self, ev_result=True):
        # This is the callback from our request player add event.
        # Don't call it directly.

        if ev_result is False:
            self.debug_log("Request to add player has been denied.")
            return False
        else:
            player = Player(self.machine, len(self.player_list))
            self.player_list.append(player)
            self.num_players = len(self.player_list)
            return player

    def player_turn_start(self):
        """Called at the beginning of a player's turn.

        Note this method is only called when a new player is first up. So if
        the same player shoots again due to an extra ball, this method is not
        called again.
        """
        self.machine.events.post('player_turn_start', player=self.player,
                                 number=self.player.number,
                                 callback=self._player_turn_starting)
        '''event: player_turn_start
        desc: A new player's turn will start. This event is only posted before the
        start of a new player's turn. If that player gets an extra ball and
        shoots again, this event is not posted a second time.

        args:
        player: The player object whose turn is starting.
        number: The player number
        '''

    def _player_turn_starting(self, **kwargs):
        del kwargs
        self.machine.events.post_queue('player_turn_starting', player=self.player,
                                       number=self.player.number,
                                       callback=self._player_turn_started)
        '''event: player_turn_starting
        desc: A new player's turn is starting. This event is only posted at the
        start of a new player's turn. If that player gets an extra ball and
        shoots again, this event is not posted a second time.

        args:
        player: The player object whose turn is starting.
        number: The player number
        '''

    def player_turn_stop(self):
        """Called when player turn stopped."""
        if not self.player:
            return

        self.machine.events.post('player_turn_stop', player=self.player,
                                 number=self.player.number)
        '''event: player_turn_stop
        desc: The player's turn is ending. This event is only posted when this
        player's turn is totally over. If the player gets an extra ball and
        shoots again, this event is not posted until after all their extra
        balls and it's no longer their turn.

        args:
        player: The player object whose turn is over.
        number: The player number
        '''

    def _player_turn_started(self, **kwargs):
        del kwargs
        self.player.ball += 1
        '''player_var: ball

        desc: The ball number for this player. If a player gets an extra ball,
        this number won't change when they start the extra ball.
        '''

        self.machine.events.post('player_turn_started', player=self.player,
                                 number=self.player.number)
        '''event: player_turn_started
        desc: A new player's turn started. This event is only posted after the
        start of a new player's turn. If that player gets an extra ball and
        shoots again, this event is not posted a second time.

        args:
        player: The player object whose turn is starting.
        number: The player number
        '''

        self.ball_starting()

    def player_rotate(self):
        """Rotate the game to the next player.

        This method is called after a player's turn is over, so it's even used
        in single-player games between balls.

        All it does really is set :attr:`player` to the next player's number.

        Args:
        """
        self.machine.events.post_queue('player_turn_ending', player=self.player,
                                       number=self.player.number,
                                       callback=self._player_rotate2)
        '''event: player_turn_ending
        desc: A player's turn is ending.

        args:
        player: The player object whose turn is ending.
        number: The player number
        '''

    def _player_rotate2(self, **kwargs):
        del kwargs
        self.player_turn_stop()

        if self.player.number < self.num_players:
            self.player = self.player_list[self.player.number]
            # Note the above line is kind of confusing but it works because
            # the current player number is always 1 more than the index.
            # i.e. "Player 1" has an index of 0, etc. So using the current
            # player number as the next player's index works out.
        else:
            self.player = self.player_list[0]

        self.debug_log("Player rotate: Now up is Player %s",
                       self.player.number)

        self.player_turn_start()

# todo player events should come next, including tracking inc/dec, other values
