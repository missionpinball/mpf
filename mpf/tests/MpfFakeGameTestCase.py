"""Test case to start and stop games without ball devices."""
from unittest.mock import MagicMock

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class MpfFakeGameTestCase(MpfGameTestCase):

    """Test case for a game that does not require ball devices & start switches.
    
    Often times you need to write a test that is able to start a game. However
    in order to start a game, MPF requires lots of things, like having proper
    ball devices and a start button and stuff like that.
    
    This test overwrites the ``start_game()`` and ``drain_ball()`` methods
    of the ``MpfGameTestCase`` class so that you can start games and drain
    balls without actually having any ball devices configured.
    
    """

    def __init__(self, methodName):
        """Patch minimal config into machine."""
        super().__init__(methodName)
        self.machine_config_patches['machine'] = dict()
        self.machine_config_patches['machine']['min_balls'] = 0

    def start_game(self, num_balls_known=3):
        """Start a game.
        
        Does not require ball devices or a start button to be present in the
        config file. Sets the number of known balls to 3.
        
        """
        def _add_ball(**kwargs):
            del kwargs
            self.machine.playfield.balls += 1
            self.machine.playfield.available_balls += 1

        # game start should work
        self.machine.playfield.add_ball = _add_ball
        self.machine.ball_controller.num_balls_known = num_balls_known
        super().start_game()

    def drain_all_balls(self):
        """Drain all the balls in play.
        
        Does not actually require any ball devices to be present in the config
        file.
        
        """
        for _ in range(self.machine.game.balls_in_play):
            self.post_event_with_params("ball_drain", balls=1)
        self.machine.playfield.balls = 0
        self.machine.playfield.available_balls = 0
        self.advance_time_and_run()

    def drain_one_ball(self):
        """Drain one ball.

        Does not actually require any ball devices to be present in the config
        file.

        """
        self.post_event_with_params("ball_drain", balls=1)
        self.machine.playfield.balls -= 1
        self.machine.playfield.available_balls -= 1
        self.advance_time_and_run()