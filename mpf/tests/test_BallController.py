"""Test the BallController."""
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallControllerRegression(MpfTestCase):

    def setUp(self):
        super().setUp()
        #self.machine.ball_controller.num_balls_known = 0

    def get_config_file(self):
        return 'regression.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_controller/'

    def get_platform(self):
        return 'virtual'

    def test_regression(self):
        self.release_switch_and_run("s_shooter_lane", 4)
        self.hit_switch_and_run("s_trough_5", .1)
        self.hit_switch_and_run("s_underRightRampEject", .1)
        self.release_switch_and_run("s_underRightRampEject", .2)
        self.hit_switch_and_run("s_trough_6", .2)
        self.hit_switch_and_run("s_underRightRampEject", .1)
        self.release_switch_and_run("s_underRightRampEject", .2)
        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertBallsOnPlayfield(0)
        self.assertAvailableBallsOnPlayfield(0)

class TestBallController(MpfTestCase):
    def setUp(self):
        super().setUp()
        self.machine.ball_controller.num_balls_known = 0

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
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
        self.advance_time_and_run(.01)
        # ball did not settle yet
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.assertEqual(None, self.machine.game)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)

    def test_ball_collect(self):
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        # prevent smart_virtual from "ejecting" the ball
        self.machine.coils["eject_coil2"].pulse = MagicMock()

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.assertEqual("idle", self.machine.ball_devices["test_trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["test_launcher"]._state)

        # not all balls are home. it should trigger a collect
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(.1)
        self.assertEqual(None, self.machine.game)

        # ball is still in launcher and the collect ball should not try to eject it again (which would request a ball
        # at the trough. so check that trough is idle
        self.assertEqual("idle", self.machine.ball_devices["test_trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["test_launcher"]._state)

    def test_ball_collect_after_game(self):
        self.mock_event("collecting_balls_complete")
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        # eject one ball to launcher
        self.machine.ball_devices["test_trough"].eject(target=self.machine.ball_devices["test_launcher"])
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.ball_devices["test_trough"].available_balls)
        self.assertEqual(1, self.machine.ball_devices["test_launcher"].available_balls)

        # assume the game ended and we want to collect all balls
        self.machine.ball_controller.collect_balls()
        self.advance_time_and_run(1)

        self.assertEqual("idle", self.machine.ball_devices["test_trough"]._state)
        self.assertEqual("ball_left", self.machine.ball_devices["test_launcher"]._state)
        self.assertEqual(3, self.machine.ball_devices["test_trough"].available_balls)
        self.assertEqual(0, self.machine.ball_devices["test_launcher"].available_balls)

        self.advance_time_and_run(11)

        # both devices should be idle
        self.assertEqual("idle", self.machine.ball_devices["test_trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["test_launcher"]._state)
        self.assertEqual(3, self.machine.ball_devices["test_trough"].available_balls)
        self.assertEqual(0, self.machine.ball_devices["test_launcher"].available_balls)
        self.assertEqual(3, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["test_launcher"].balls)
        self.assertEqual(0, self._events['collecting_balls_complete'])

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["test_trough"])
        self.advance_time_and_run(1)

        self.assertEqual(1, self._events['collecting_balls_complete'])

    def test_ball_collect_without_balls_on_pf(self):
        self.mock_event("collecting_balls_complete")
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.machine.ball_controller.collect_balls()
        self.advance_time_and_run(1)

        self.assertEqual(1, self._events['collecting_balls_complete'])

    def test_unknown_ball_on_playfield(self):
        self.mock_event("collecting_balls_complete")
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 0)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        self.hit_and_release_switch("s_playfield")
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self.machine.playfield.available_balls)
        self.assertEqual(0, self.machine.playfield.balls)

        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

    def test_loose_balls(self):
        self.mock_event("collecting_balls_complete")
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.machine.switch_controller.process_switch("s_ball_switch3", 0)
        self.machine.switch_controller.process_switch("s_ball_switch4", 0)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
