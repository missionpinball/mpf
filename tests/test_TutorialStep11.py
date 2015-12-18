
from .MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep11(MpfTestCase):

    def getConfigFile(self):
        return 'step11.yaml'

    def getMachinePath(self):
        return '../machine_files/tutorial/'

    def get_platform(self):
        return 'smart_virtual'

    def test_game(self):
        # start active switches should start with 5 balls in the trough

        self.machine.ball_controller.num_balls_known = 5
        self.assertEqual(5, self.machine.ball_devices.bd_trough.balls)

        # player hits start
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.advance_time_and_run(2)

        self.assertEqual(1, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(2)

        # ball is on the pf
        self.machine.switch_controller.process_switch('s_right_inlane', 1)
        self.machine.switch_controller.process_switch('s_right_inlane', 0)
        self.advance_time_and_run(2)

        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(0, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

        # ball drains, game goes to ball 2
        self.machine.default_platform.add_ball_to_device(
            self.machine.ball_devices.bd_trough)

        self.advance_time_and_run(1)

        self.assertEqual(2, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)

        # repeat above cycle for ball 2

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(2)

        # ball is on the pf
        self.machine.switch_controller.process_switch('s_right_inlane', 1)
        self.machine.switch_controller.process_switch('s_right_inlane', 0)
        self.advance_time_and_run(2)

        self.assertEqual(2, self.machine.game.player.ball)
        self.assertEqual(0, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

        # ball drains, game goes to ball 3
        self.machine.default_platform.add_ball_to_device(
            self.machine.ball_devices.bd_trough)

        self.advance_time_and_run(1)

        self.assertEqual(3, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)

        # repeat above cycle for ball 3

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(2)

        # ball is on the pf

        # this time let's test the timeout with no pf switch hit
        # self.machine.switch_controller.process_switch('s_right_inlane', 1)
        # self.machine.switch_controller.process_switch('s_right_inlane', 0)
        self.advance_time_and_run(2)

        self.assertEqual(3, self.machine.game.player.ball)
        self.assertEqual(0, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

        # ball drains, game ends
        self.machine.default_platform.add_ball_to_device(
            self.machine.ball_devices.bd_trough)

        self.advance_time_and_run(1)

        self.assertIsNone(self.machine.game)
        self.assertEqual(0, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(5, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
