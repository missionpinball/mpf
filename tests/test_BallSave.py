from tests.MpfTestCase import MpfTestCase


class TestBallSave(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_save/'

    def get_platform(self):
        return 'smart_virtual'

    def testBallSaveShootAgain(self):
        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.ball_saves.default.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # ball save should be enabled now
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # ball drains right away
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(0, self.machine.playfield.balls)

        # ball save disables because no ball to be saved remain
        self.assertFalse(self.machine.ball_saves.default.enabled)

        # game should eject another ball
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # ball drains also
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def hurry_up(self, **kwargs):
        self._hurry_up = True

    def grace_period(self, **kwargs):
        self._grace_period = True

    def testBallSaveEvents(self):
        self.machine.events.add_handler("ball_save_default_hurry_up", self.hurry_up)
        self.machine.events.add_handler("ball_save_default_grace_period", self.grace_period)
        self._hurry_up = False
        self._grace_period = False

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.ball_saves.default.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # ball save should be enabled now
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)

        self.assertEqual(1, self.machine.playfield.balls)
        self.assertFalse(self._hurry_up)
        self.assertFalse(self._grace_period)
        self.assertTrue(self.machine.ball_saves.default.enabled)

        self.advance_time_and_run(8)
        self.assertTrue(self._hurry_up)
        self.assertFalse(self._grace_period)
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # should be active for another 2s + 2s grace period
        self.assertTrue(self.machine.ball_saves.default.enabled)
        self.advance_time_and_run(2)
        self.assertTrue(self._grace_period)
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # after another 2s it should turn off
        self.advance_time_and_run(2)
        self.assertFalse(self.machine.ball_saves.default.enabled)

        # game should still run
        self.assertNotEqual(None, self.machine.game)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)