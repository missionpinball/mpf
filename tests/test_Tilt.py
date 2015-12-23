import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestTilt(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/tilt/'

    def get_platform(self):
        return 'smart_virtual'

    def _tilted(self):
        self._is_tilted = True

    def test_simple_tilt(self):
        self._is_tilted = False
        self.machine.events.add_handler("tilt", self._tilted)

        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(2)

        self.assertEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.advance_time_and_run(10)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_tilt', 1)
        self.machine.switch_controller.process_switch('s_tilt', 0)
        self.advance_time_and_run(1)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(None, self.machine.game)

    def test_simple_tilt_ball_not_on_pf_yet(self):
        self._is_tilted = False
        self.machine.events.add_handler("tilt", self._tilted)

        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(2)

        self.assertEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.advance_time_and_run(1)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_tilt', 1)
        self.machine.switch_controller.process_switch('s_tilt', 0)
        self.advance_time_and_run(.1)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(None, self.machine.game)
