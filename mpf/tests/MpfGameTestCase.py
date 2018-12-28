"""Test case to start and stop games."""
from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class MpfGameTestCase(MpfTestCase):

    """Test case for starting and running games.
    
    This is based on ``MpfTestCase`` but adds methods and assertions related
    to running games (rather than just testing MPF components or devices).
    
    """

    def __init__(self, methodName):
        """Patch minimal config needed to start a game into the machine config.
        
        This method adds a switch called ``s_start`` with a tag called
        ``start``.
        
        """
        super().__init__(methodName)
        self.machine_config_patches['switches'] = dict()
        self.machine_config_patches['switches']['s_start'] = {"number": "", "tags": "start"}

    def start_two_player_game(self):
        """Start two player game."""
        self.start_game()
        self.add_player()

    def fill_troughs(self):
        """Fill all ball devices tagged with  ``trough`` with balls."""
        for trough in self.machine.ball_devices.items_tagged("trough"):
            for switch in trough.config['ball_switches']:
                self.hit_switch_and_run(switch.name, 0)

        self.advance_time_and_run()

    def start_game(self):
        """Start a game.
        
        This method checks to make sure a game is not running,
        then hits and releases the ``s_start`` switch, and
        finally checks to make sure a game actually started
        properly.
        
        For example:
        
        .. code::
        
            self.start_game()
        
        """
        # game start should work
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsRunning()
        self.assertEqual(1, self.machine.game.num_players)
        self.assertPlayerNumber(1)

    def add_player(self):
        """Add a player to the current game.
        
        This method hits and releases a switch called ``s_start``
        and then verifies that the player count actually increased
        by 1.
        
        You can call this method multiple times to add multiple
        players. For example, to start a game and then add 2 additional
        players (for 3 players total), you would use:
        
        .. code::
        
            self.start_game()
            self.add_player()
            self.add_player()
        
        """
        prev_players = self.machine.game.num_players
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(1)
        self.assertEqual(prev_players + 1, self.machine.game.num_players)

    def assertBallNumber(self, number):
        """Asserts that the current ball is a certain ball numebr.
        
        Args:
            number: The number to check.
        
        Raises:
            Assertion error if there is no game in progress or if
            the current ball is not the ball number passed.
            
        The following code will check to make sure the game is on
        Ball 1:
        
        .. code::
        
            self.assertBallNumber(1)
        
        """
        self.assertGameIsRunning()
        self.assertEqual(number, self.machine.game.player.ball)

    def assertBallsInPlay(self, balls):
        """Asserts that a certain number of balls are in play.
        
        Note that the number of balls in play is not necessarily the same as
        the number of balls on the playfield. (For example, a ball could
        be held in a ball device, or the machine could be in the process
        of adding a ball to the platfield.)
        
        Args:
            balls: The number of balls you want to assert are in
                play.
        
        To assert that there are 3 balls in play (perhaps during a multiball),
        you would use:
        
        .. code::
        
            self.assertBallsInPlay(3)
        
        """
        self.assertEqual(balls, self.machine.game.balls_in_play)

    def drain_all_balls(self):
        """Drain a single ball.
        
        If more than 1 ball is in play, this method will need to
        be called once for each ball in order to end the current
        ball.
        
        For example, if you have a three-ball multiball and you want
        to drain all the balls (and end the ball), you would use:
        
        .. code::
        
            self.drain_ball()
            self.drain_ball()
            self.drain_ball()
        
        """
        drain = self.machine.ball_devices.items_tagged("drain")[0]
        self.machine.default_platform.add_ball_to_device(drain)

    def assertPlayerNumber(self, number):
        """Asserts that the current player is a certain player number.
        
        Args:
            number: The player number you can to assert is the current
                player.
        
        For example, to assert that the current player is Player 2, you
        would use:
        
        .. code::
        
            self.assertPlayerNumber(2)
        
        """
        self.assertEqual(number, self.machine.game.player.index + 1)

    def assertPlayerCount(self, count):
        """Asserts that count players exist.

        Args:
            count: The expected number of players.

        For example, to assert that the to players are in the game:

        .. code::

            self.assertPlayerCount(2)

        """
        self.assertEqual(count, len(self.machine.game.player_list))

    def stop_game(self, stop_time=1):
        """Stop the current game.
        
        This method asserts that a game is running, then call's
        the game mode's ``end_game()`` method, then asserts that
        the game has successfully stopped.
        
        Example:
            
        .. code::
        
            self.stop_game()
        
        """
        self.assertGameIsRunning()
        self.machine.game.end_game()
        self.advance_time_and_run(stop_time)
        self.assertGameIsNotRunning()

    def assertGameIsRunning(self):
        """Assert a game is running.
        
        Example:
            
        .. code::
        
            self.assertGameIsRunning()
        
        """
        self.assertIsNotNone(self.machine.game, "Expected a running game but no game is active.")

    def assertGameIsNotRunning(self):
        """Assert a game is not running.
        
        Example:
            
        .. code::
        
            self.assertGameIsNotRunning()
        
        """
        self.assertIsNone(self.machine.game, "Expected game to have ended but game is active.")
