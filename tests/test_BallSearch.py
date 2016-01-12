import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallSearch(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_search/'

    def get_platform(self):
        return 'smart_virtual'

    def test_game_with_no_switches(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        # wait for eject_timeout of launcher
        self.advance_time_and_run(6)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)

        # vuk should reset the timer
        self.machine.switch_controller.process_switch("s_vuk", 1)
        # wait for eject_timeout of vuk
        self.advance_time_and_run(3)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        self.advance_time_and_run(15)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.advance_time_and_run(5)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

    def test_game_with_switches(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)

        # vuk should reset the timer
        self.machine.switch_controller.process_switch("s_vuk", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        self.advance_time_and_run(15)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.advance_time_and_run(5)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

    def test_ball_search_iterations(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)

        self.advance_time_and_run(15)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        # this will break smart_virtual
        self.machine.coils['eject_coil1'].pulse = MagicMock()
        self.machine.coils['eject_coil2'].pulse = MagicMock()
        self.machine.coils['eject_coil3'].pulse = MagicMock()
        self.machine.coils['hold_coil'].pulse = MagicMock()

        self.advance_time_and_run(5)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        self.machine.ball_devices['playfield'].add_ball = MagicMock()

        for i in range(1,11):
                self.assertEqual(i, self.machine.ball_devices['playfield'].ball_search.iteration)

                assert not self.machine.coils['eject_coil1'].pulse.called
                self.machine.coils['eject_coil2'].pulse.assert_called_with()
                assert not self.machine.coils['eject_coil3'].pulse.called
                assert not self.machine.coils['hold_coil'].pulse.called

                self.advance_time_and_run(.25)

                assert not self.machine.coils['eject_coil1'].pulse.called
                self.machine.coils['eject_coil2'].pulse.assert_called_with()
                self.machine.coils['eject_coil3'].pulse.assert_called_with()
                assert not self.machine.coils['hold_coil'].pulse.called

                self.advance_time_and_run(.25)

                assert not self.machine.coils['eject_coil1'].pulse.called
                self.machine.coils['eject_coil2'].pulse.assert_called_with()
                self.machine.coils['eject_coil3'].pulse.assert_called_with()
                self.machine.coils['hold_coil'].pulse.assert_called_with()

                self.machine.coils['eject_coil1'].pulse = MagicMock()
                self.machine.coils['eject_coil2'].pulse = MagicMock()
                self.machine.coils['eject_coil3'].pulse = MagicMock()
                self.machine.coils['hold_coil'].pulse = MagicMock()

                assert not self.machine.ball_devices['playfield'].add_ball.called

                self.advance_time_and_run(10)


        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.machine.ball_devices['playfield'].add_ball.assert_called_with()

