
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep16(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../examples/tutorial_step_16/'

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

        # make sure the base game mode is active
        self.assertTrue(self.machine.mode_controller.is_active('base'))

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(2)

        # ball is on the pf
        # 100 points
        self.machine.switch_controller.process_switch('s_right_inlane',
                                                      1)
        self.machine.switch_controller.process_switch('s_right_inlane',
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(100, self.machine.game.player.score)

        # player should get 1000 points for hitting the flipper button
        self.machine.switch_controller.process_switch('s_left_flipper',
                                                      1)
        self.machine.switch_controller.process_switch('s_left_flipper',
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(1100, self.machine.game.player.score)
        self.advance_time_and_run(2)

        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(0, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

        # lets drop the ball in some devices and make sure it kicks it out
        self.machine.switch_controller.process_switch('s_eject', 1)
        self.advance_time_and_run(2)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

        self.machine.switch_controller.process_switch('s_bottom_popper', 1)
        self.advance_time_and_run(3)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)

        self.machine.switch_controller.process_switch('s_top_popper', 1)
        self.advance_time_and_run(3)
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

        # make sure the base game mode is not active
        self.assertFalse(self.machine.mode_controller.is_active('base'))
