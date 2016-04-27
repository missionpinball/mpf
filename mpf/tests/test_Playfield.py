import unittest

from mpf.core.machine import MachineController
from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestPlayfield(MpfTestCase):

    def getConfigFile(self):
        return 'test_playfield.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/playfield/'

    def test_unexpected_ball_on_pf(self):
        self.set_num_balls_known(1)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(False, self.machine.config['machine']['glass_off_mode'])

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

    def test_unexpected_ball_on_pf_glass_off_mode(self):
        self.set_num_balls_known(1)
        self.machine.config['machine']['glass_off_mode'] = True

        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(True, self.machine.config['machine']['glass_off_mode'])

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
