from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestTilt(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/tilt/'

    def get_platform(self):
        return 'smart_virtual'

    def _tilted(self, **kwargs):
        del kwargs
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

        # flipper actived
        self.assertTrue(self.machine.flippers.f_test._enabled)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        # scoring should work
        self.post_event("test_scoring")
        self.assertPlayerVarEqual(100, "score")

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_tilt', 1)
        self.machine.switch_controller.process_switch('s_tilt', 0)
        self.advance_time_and_run(1)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        # flipper deactived
        self.assertFalse(self.machine.flippers.f_test._enabled)

        # scoring should no longer work
        self.assertPlayerVarEqual(100, "score")
        self.post_event("test_scoring")
        self.assertPlayerVarEqual(100, "score")

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

    def test_tilt_event(self):
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
        self.machine.events.post("tilt_event")
        self.advance_time_and_run(1)
        self.machine.events.post("tilt_event")
        self.advance_time_and_run(1)
        self.machine.events.post("tilt_event")
        self.advance_time_and_run(1)

        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

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
        self.assertEqual(True, self.machine.game.tilted)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

    def test_tilt_warning(self):
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

        # multiple hits in 300ms window
        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(1)
        self.assertFalse(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(1)
        self.assertFalse(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(1)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)

        # wait for settle time (5s) since last s_tilt_warning hit
        self.advance_time_and_run(3.5)
        self.assertEqual(False, self.machine.game.tilted)

    def test_slam_tilt(self):
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

        # flipper actived
        self.assertTrue(self.machine.flippers.f_test._enabled)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_slam_tilt', 1)
        self.machine.switch_controller.process_switch('s_slam_tilt', 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)

        # flipper deactived
        self.assertFalse(self.machine.flippers.f_test._enabled)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(None, self.machine.game)

        # test that it does not crash outside the game
        self.post_event("tilt_reset_warnings")
        self.advance_time_and_run()
