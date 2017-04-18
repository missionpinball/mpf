"""Contains the Game class which is the Machine Mode that actually runs and manages an the game in a pinball machine.

Note that in the Mission Pinball Framework, a distinction is made between a
*game* and a *machine*. A *game* refers to a game in progress, whereas a
*machine* is the physical pinball machine.
"""
from functools import partial
import asyncio

from mpf.core.events import QueuedEvent
from mpf.core.async_mode import AsyncMode
from mpf.core.player import Player


class Game(AsyncMode):

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
        self._stopping_modes = []
        self._stopping_queue = None
        self._end_ball_event = None

        self.machine.events.add_handler('mode_{}_stopping'.format(self.name), self._stop_game_modes)

    @asyncio.coroutine
    def _run(self):
        """Main game mode method (basic game loop)"""

        # Init the game (game start process)

        # Initialize member variables
        self.player = None
        self.player_list = list()
        self.machine.game = self
        self.slam_tilted = False
        self.tilted = False
        self.num_players = 0
        self._balls_in_play = 0
        self._stopping_modes = []
        self._stopping_queue = None
        self._end_ball_event = asyncio.Event(loop=self.machine.clock.loop)
        self._end_ball_event.clear()

        # Add add player switch handler
        if self.machine.config['game']['add_player_switch_tag']:
            self.add_mode_event_handler(
                self.machine.config['mpf']['switch_tag_event'].replace(
                    '%', self.machine.config['game']['add_player_switch_tag']),
                self.request_player_add)

        yield from self._start_game()

        # Game loop
        while True:
            # Wait for end ball event to be set
            yield from self._end_ball_event.wait()
            if self._end_ball_event.is_set():
                yield from self._end_ball()
                self._end_ball_event.clear()

    @asyncio.coroutine
    def _start_game(self):
        """Start a new game"""

        self.debug_log("Game start")

        yield from self.machine.events.post_async('game_will_start')
        '''event: game_will_start
        desc: The game is about to start. This event is posted just before
        :doc:`game_starting`.'''

        yield from self.machine.events.post_queue_async('game_starting', game=self)
        '''event: game_starting
        desc: A game is in the process of starting. This is a queue event, and
        the game won't actually start until the queue is cleared.

        args:
        game: A reference to the game mode object.
        '''

        # Sometimes game_starting handlers will add players, so we only
        # have to add one here if there aren't any players yet.
        if not self.player_list:
            yield from self._add_player()

        self.machine.remove_machine_var_search(startswith='player',
                                               endswith='_score')

        yield from self._start_player_turn()

        yield from self.machine.events.post_async('game_started')
        '''event: game_started
        desc: A new game has started.'''

        self.debug_log("Game started")

    @asyncio.coroutine
    def _add_player(self):
        """Add a new player to the current game"""

        new_player_number = len(self.player_list) + 1

        yield from self.machine.events.post_async('player_will_add', number=new_player_number)
        '''event: player_will_add
        desc: A new player will be added to this game. This event is sent immediately
        prior to the player_adding event.

        args:
        number: The new player number that will be added
        '''

        # Actually create the new player object
        player = Player(self.machine, len(self.player_list))

        self.player_list.append(player)
        self.num_players = len(self.player_list)

        yield from self.machine.events.post_queue_async('player_adding',
                                                        player=player,
                                                        number=player.number)
        '''event: player_adding
        desc: A new player is in the process of being added to this game. This is a queue 
        event, and the player won't actually be finished adding until the queue is cleared.

        args:
        player: The player object for the player being added
        number: The player number
        '''

        yield from self.machine.events.post_async('player_added',
                                                  player=player,
                                                  num=player.number)
        '''event: player_added

        desc: A new player was just added to this game

        args:

        player: A reference to the instance of the Player() object.

        num: The number of the player that was just added. (e.g. Player 1 will
        have *num=1*, Player 4 will have *num=4*, etc.)

        '''

        self.info_log("Player added successfully. Total players: %s", self.num_players)

        if self.num_players == 2:
            yield from self.machine.events.post_async('multiplayer_game')
            '''event: multiplayer_game
            desc: A second player has just been added to this game, meaning
            this is now a multiplayer game.

            This event is typically used to switch the score display from the
            single player layout to the multiplayer layout.'''

        # Enable player variable events and send all initial values
        player.enable_events(True, True)

        # Create machine variable to hold new player's score
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

    def ball_ending(self):
        """DEPRECATED in v0.50. Use end_ball() instead."""
        # TODO: Remove this function as it has been deprecated and replaced
        self.warning_log("game.ball_ending() function has been deprecated. "
                         "Please use game.end_ball() instead.")
        self.end_ball()

    def end_ball(self):
        """Sets an event flag that will end the current ball"""
        self._end_ball_event.set()

    @asyncio.coroutine
    def _end_ball(self):
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

        self.debug_log("Entering Game._end_ball()")

        yield from self.machine.events.post_async('ball_will_end')
        '''event: ball_will_end
        desc: The ball is about to end. This event is posted just before
        :doc:`ball_ending`.'''

        yield from self.machine.events.post_queue_async('ball_ending')
        '''event: ball_ending
        desc: The ball is ending. This is a queue event and the ball won't
        actually end until the queue is cleared.

        This event is posted just after :doc:`ball_will_end`'''

        yield from self.machine.events.post_async('ball_ended')
        '''event: ball_ended
        desc: The ball has ended.
    
        Note that this does not necessarily mean that the next player's turn
        will start, as this player may have an extra ball which means they'll
        shoot again.'''

        self.debug_log("Ball has ended")

        if self.slam_tilted:
            yield from self._end_game()
            return

        if self.player.extra_balls:
            self.award_extra_ball()
            return

        if (self.player.ball == self.machine.config['game']['balls_per_game'] and
                    self.player.number == self.num_players):
            yield from self._end_game()
        else:
            yield from self._rotate_players()
            yield from self._start_player_turn()

    @property
    def balls_in_play(self) -> int:
        """Return balls in play."""
        return self._balls_in_play

    @balls_in_play.setter
    def balls_in_play(self, value: int):
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
            # Trigger end ball process by setting event
            self._end_ball_event.set()

    def _stop_game_modes(self, queue: QueuedEvent, **kwargs):
        """Stop all game modes and wait until they stopped."""
        del kwargs
        self._stopping_modes = []
        for mode in self.machine.modes.values():
            if mode.is_game_mode and mode.active:
                self._stopping_modes.append(mode)
                mode.stop(callback=partial(self._game_mode_stopped, mode=mode))

        if self._stopping_modes:
            queue.wait()
            self._stopping_queue = queue

    def _game_mode_stopped(self, mode):
        """Mark game mode stopped and clear the wait on stop if this was the last one."""
        self._stopping_modes.remove(mode)
        if not self._stopping_modes:
            self._stopping_queue.clear()
            self._stopping_queue = None

    def mode_stop(self, **kwargs):
        """Stop mode."""
        for mode in self.machine.modes:
            if mode.active and mode.is_game_mode:
                raise AssertionError("Mode {} is not supposed to run outside of game.".format(mode.name))
        self.machine.game = None

    @asyncio.coroutine
    def _start_ball(self, is_extra_ball=False):
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

        yield from self.machine.events.post_async('ball_will_start',
                                                  is_extra_ball=is_extra_ball)
        '''event: ball_will_start
        desc: The ball is about to start. This event is posted just before
        :doc:`ball_starting`.'''

        yield from self.machine.events.post_queue_async(
            'ball_starting',
            balls_remaining=self.machine.config['game']['balls_per_game'] - self.player.ball,
            is_extra_ball=is_extra_ball)
        '''event: ball_starting
        desc: A ball is starting. This is a queue event, so the ball won't
        actually start until the queue is cleared.'''

        # register handlers to watch for ball drain and live ball removed
        self.add_mode_event_handler('ball_drain', self.ball_drained)

        self.balls_in_play = 1

        self.debug_log("ball_started for Ball %s", self.player.ball)

        yield from self.machine.events.post_async('ball_started',
                                                  ball=self.player.ball,
                                                  player=self.player.number)
        '''event: ball_started
        desc: A new ball has started.
        args:
        ball: The ball number.
        player: The player number.'''

        if self.num_players == 1:
            yield from self.machine.events.post_async('single_player_ball_started')
            '''event: single_player_ball_started
            desc: A new ball has started, and this is a single player game.'''
        else:
            yield from self.machine.events.post_async('multi_player_ball_started')
            '''event: multi_player_ball_started
            desc: A new ball has started, and this is a multiplayer game.'''
            yield from self.machine.events.post_async(
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

    @asyncio.coroutine
    def _end_game(self):
        self.debug_log("Entering Game._end_game()")

        yield from self.machine.events.post_async('game_will_end')
        '''event: game_will_end
        desc: The game is about to end. This event is posted just before
        :doc:`game_ending`.'''

        yield from self.machine.events.post_queue_async('game_ending')
        '''event: game_ending
        desc: The game is in the process of ending. This is a queue event, and
        the game won't actually end until the queue is cleared.'''

        yield from self._end_player_turn()

        yield from self.machine.events.post_async('game_ended')
        '''event: game_ended
        desc: The game has ended.'''

    def game_ending(self):
        """Called when the game decides it should end.

        This method posts the queue event *game_ending*, giving other modules
        an opportunity to finish up whatever they need to do before the game
        ends. Once all the registered handlers for that event have finished,
        this method calls :meth:`game_end`.

        """
        self.machine.clock.loop.run_until_complete(self._end_game)

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
        *player_added* is posted with a reference to the new player
        object as a *player* kwarg.

        """
        del kwargs
        self.debug_log("Received request to add player.")

        # There area few things we have to check first. If this all passes,
        # then we'll raise the event to ask other modules if it's ok to add a
        # player

        if len(self.player_list) >= self.machine.config['game']['max_players']:
            self.debug_log("Game is at max players. Cannot add another.")
            return False

        if self.player and self.player.ball > 1:  # todo config setting
            self.debug_log("Current ball is after Ball 1. Cannot add player.")
            return False

        result = self.machine.events.post_boolean('player_add_request',
                                                  callback=self._player_add_request_complete)
        '''event: player_add_request
        desc: Posted to request that an additional player be added to this
        game. Any registered handler can deny the player add request by
        returning *False* to this event.
        '''
        return result

    def _player_add_request_complete(self, ev_result=True) -> bool:
        """This is the callback from our request player add event."""
        # Don't call it directly.

        if ev_result is False:
            self.debug_log("Request to add player has been denied.")
            return False

        # Call the method to actually add the player
        self.machine.clock.loop.run_until_complete(self._add_player())
        return True

    @asyncio.coroutine
    def _start_player_turn(self):
        """Called at the beginning of a player's turn.

        Note this method is only called when a different player's turn is up. 
        So if the same player shoots again due to an extra ball, this method 
        is not called again.
        """
        # If we get a request to start a turn but we haven't done a rotate to
        # set the first player, do that now.
        if not self.player:
            yield from self._rotate_players()

        yield from self.machine.events.post_async('player_turn_will_start',
                                                  player=self.player,
                                                  number=self.player.number)
        '''event: player_turn_will_start
        desc: A new player's turn will start. This event is only posted before the
        start of a new player's turn. If that player gets an extra ball and
        shoots again, this event is not posted a second time.

        args:
        player: The player object whose turn is starting.
        number: The player number
        '''

        yield from self.machine.events.post_queue_async('player_turn_starting',
                                                        player=self.player,
                                                        number=self.player.number)
        '''event: player_turn_starting
        desc: The player's turn is in the process of starting. This is a queue 
        event, and the player's turn won't actually start until the queue is cleared.

        args:
        player: The player object whose turn is starting.
        number: The player number
        '''

        self.player.ball += 1
        '''player_var: ball
    
        desc: The ball number for this player. If a player gets an extra ball,
        this number won't change when they start the extra ball.
        '''

        yield from self.machine.events.post_async('player_turn_started',
                                                  player=self.player,
                                                  number=self.player.number)
        '''event: player_turn_started
        desc: A new player's turn started. This event is only posted after the
        start of a new player's turn. If that player gets an extra ball and
        shoots again, this event is not posted a second time.
    
        args:
        player: The player object whose turn is starting.
        number: The player number
        '''

        yield from self._start_ball()

    @asyncio.coroutine
    def _end_player_turn(self):
        """Ends the current player's turn"""
        if not self.player:
            return

        yield from self.machine.events.post_async('player_turn_will_end',
                                                  player=self.player,
                                                  number=self.player.number)
        '''event: player_turn_will_end
        desc: The player's turn is about to end. This event is only posted when this
        player's turn is totally over. If the player gets an extra ball and
        shoots again, this event is not posted until after all their extra
        balls and it's no longer their turn.

        args:
        player: The player object whose turn is over.
        number: The player number
        '''

        yield from self.machine.events.post_queue_async('player_turn_ending',
                                                        player=self.player,
                                                        number=self.player.number)
        '''event: player_turn_ending
        desc: The current player's turn is ending. This is a queue event, and 
        the player's turn won't actually end until the queue is cleared.

        args:
        player: The player object whose turn is ending.
        number: The player number
        '''

        # Update player's score before changing turns
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

        yield from self.machine.events.post_async('player_turn_ended',
                                                  player=self.player,
                                                  number=self.player.number)
        '''event: player_turn_ended
        desc: The current player's turn has ended. This event is only posted when 
        this player's turn is totally over. If the player gets an extra ball and
        shoots again, this event is not posted until after all their extra balls 
        and it's no longer their turn.

        args:
        player: The player object whose turn is ending.
        number: The player number
        '''

    @asyncio.coroutine
    def _rotate_players(self):
        """Rotate the game to the next player.

        This method is called after a player's turn is over, so it's even used
        in single-player games between balls.

        All it does really is set :attr:`player` to the next player's number.
        """
        # todo  do cool stuff in the future to change order, etc.

        if self.player:
            yield from self._end_player_turn()
        else:
            # no current player, grab the first one
            self.player = self.player_list[0]

        self.debug_log("Player rotate: Now up is Player %s",
                       self.player.number)

# todo player events should come next, including tracking inc/dec, other values
