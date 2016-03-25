from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock


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

    def test_ball_collect(self):
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.machine.switch_controller.process_switch("s_ball_switch4", 1)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        # prevent smart_virtual from "ejecting" the ball
        self.machine.coils.eject_coil2.pulse = MagicMock()

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(.5)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.assertEqual("idle", self.machine.ball_devices.test_trough._state)
        self.assertEqual("ejecting", self.machine.ball_devices.test_launcher._state)

        # not all balls are home. it should trigger a collect
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(.1)
        self.assertEqual(None, self.machine.game)

        # ball is still in launcher and the collect ball should not try to eject it again (which would request a ball
        # at the trough. so check that trough is idle
        self.assertEqual("idle", self.machine.ball_devices.test_trough._state)
        self.assertEqual("ejecting", self.machine.ball_devices.test_launcher._state)
