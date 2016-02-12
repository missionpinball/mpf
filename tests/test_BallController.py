import unittest

from mpf.core.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time


class TestBallController(MpfTestCase):
    def setUp(self):
        super().setUp()
        self.machine.ball_controller.num_balls_known = 0

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_controller/'

    def get_platform(self):
        return 'smart_virtual'

    def test_game_start(self):
        # min balls is set to 3
        self.assertEqual(None, self.machine.game)
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)
        self.assertEqual(0, self.machine.ball_controller.num_balls_known)

        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # not enough balls
        self.assertEqual(None, self.machine.game)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        # not all balls are home
        self.assertEqual(None, self.machine.game)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.assertEqual(None, self.machine.game)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
