from mpf.tests.MpfTestCase import MpfTestCase


class TestExtraBallDisabled(MpfTestCase):

    def getConfigFile(self):
        return 'disabled.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/extra_ball/'

    def get_platform(self):
        return 'smart_virtual'

    def test_extra_ball_disabled(self):
        # prepare game
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # add second player
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        self.assertEqual(2, len(self.machine.game.player_list))

        # start mode
        self.post_event("start_mode1")

        # mode loaded. ball_lock2 should be enabled
        self.assertTrue(self.machine.extra_balls.test_extra_ball)
        self.assertTrue(self.machine.extra_balls.test_extra_ball.player)
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(False, self.machine.game.player.extra_balls_awarded['test_extra_ball'])
        self.assertEqual(0, self.machine.game.player.extra_balls)

        # stop mode
        self.post_event("stop_mode1")

        # nothing should happen
        self.post_event("extra_ball_award")
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(False, self.machine.game.player.extra_balls_awarded['test_extra_ball'])
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertFalse(self.machine.extra_balls.test_extra_ball.player)

        # start mode (again)
        self.post_event("start_mode1")

        self.assertTrue(self.machine.extra_balls.test_extra_ball)
        self.assertTrue(self.machine.extra_balls.test_extra_ball.player)
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(False, self.machine.game.player.extra_balls_awarded['test_extra_ball'])
        self.assertEqual(0, self.machine.game.player.extra_balls)

        # player get extra_ball
        self.post_event("extra_ball_award")

        # but it does nothing
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(0, self.machine.game.player.extra_balls_awarded['test_extra_ball'])
        self.assertEqual(0, self.machine.game.player.extra_balls)