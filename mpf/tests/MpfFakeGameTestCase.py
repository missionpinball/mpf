"""Testcase to start and stop games without ball devices."""
from unittest.mock import MagicMock

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class MpfFakeGameTestCase(MpfGameTestCase):

    """Testcase for fake game."""

    def __init__(self, methodName):
        """Patch minimal config into machine."""
        super().__init__(methodName)
        self.machine_config_patches['machine'] = dict()
        self.machine_config_patches['machine']['min_balls'] = 0

    def start_game(self):
        # game start should work
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        super().start_game()
