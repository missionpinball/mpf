from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestBallSave(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_save/'

    def get_platform(self):
        return 'smart_virtual'

    def test_ball_save_enable_in_mode(self):
        # start mode
        self.post_event("start_mode1")

        # mode loaded. mode_ball_save should be enabled
        self.assertTrue(self.machine.ball_saves.mode_ball_save.enabled)

        # stop mode
        self.post_event("stop_mode1")

        # mode stopped. mode_ball_save should be disabled
        self.assertFalse(self.machine.ball_saves.mode_ball_save.enabled)

    def test_early_ball_save_once(self):
        # prepare game
        self.fill_troughs()
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.start_game()
        self.post_event("enable1")

        # ball save should be enabled now
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # early ball save
        self.hit_and_release_switch("s_left_outlane")

        # should eject a second ball
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertBallsOnPlayfield(2)
        self.assertFalse(self.machine.ball_saves.default.enabled)
        self.assertBallsInPlay(1)

        # second ball drains
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        # game should not end and ball should not come back
        self.assertNotEqual(None, self.machine.game)

        self.advance_time_and_run(10)
        self.assertBallsOnPlayfield(1)

        # second ball draining should end the game
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.assertEqual(None, self.machine.game)

    def test_early_ball_save_unlimited(self):
        # prepare game
        self.fill_troughs()
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.start_game()
        self.post_event("enable2")

        # ball save should be enabled now
        self.assertTrue(self.machine.ball_saves.unlimited.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)
        self.assertTrue(self.machine.ball_saves.unlimited.enabled)

        # early ball save
        self.hit_and_release_switch("s_left_outlane")

        # should eject a second ball
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertBallsOnPlayfield(2)
        self.assertTrue(self.machine.ball_saves.unlimited.enabled)
        self.assertBallsInPlay(1)

        # second ball drains
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        # game should not end and ball should not come back
        self.assertNotEqual(None, self.machine.game)

        self.advance_time_and_run(10)
        self.assertBallsOnPlayfield(1)

        # second ball draining should be saved
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.assertNotEqual(None, self.machine.game)
        self.assertBallsOnPlayfield(0)

        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(1)

    def testBallSaveShootAgain(self):
        # prepare game
        self.fill_troughs()
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.ball_saves.default.enabled)

        # start game
        self.start_game()
        self.post_event("enable1")

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
        self.mock_event("ball_save_default_timer_start")
        self._hurry_up = False
        self._grace_period = False

        # prepare game
        self.fill_troughs()
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.ball_saves.default.enabled)
        self.assertEqual(0, self._events["ball_save_default_timer_start"])

        # start game
        self.start_game()
        self.post_event("enable1")

        # ball save should be enabled now
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(3)
        self.assertEqual(1, self._events["ball_save_default_timer_start"])
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

    def testBallSaveUnlimited(self):
        self.mock_event("ball_save_unlimited_timer_start")

        # prepare game
        self.fill_troughs()
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.ball_saves.unlimited.enabled)
        self.assertEqual(0, self._events["ball_save_unlimited_timer_start"])

        # start game
        self.start_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(10)
        self.assertEqual(0, self._events["ball_save_unlimited_timer_start"])

        # ball save should be enabled now
        self.post_event("enable2")
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.ball_saves.unlimited.enabled)
        self.assertTrue(self.machine.ball_saves.unlimited.unlimited_saves)
        self.assertEqual(1, self._events["ball_save_unlimited_timer_start"])

        # 20s loop
        for i in range(4):
            # ball drains
            self.machine.switch_controller.process_switch('s_ball_switch1', 1)
            self.machine.switch_controller.process_switch('s_ball_switch2', 1)
            self.advance_time_and_run(1)
            self.assertEqual(0, self.machine.playfield.balls)

            # wait for new ball
            self.advance_time_and_run(4)
            self.assertNotEqual(None, self.machine.game)
            self.assertEqual(1, self.machine.playfield.balls)

        # after 30s + 2s + 2s it should turn off
        self.advance_time_and_run(15)
        self.assertFalse(self.machine.ball_saves.unlimited.enabled)

        # game should still run
        self.assertNotEqual(None, self.machine.game)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testBallOutsideGame(self):
        self.assertEqual(None, self.machine.game)

        # enable ball save
        self.post_event("enable1")
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.playfield.balls)

        # it should not come back
        self.advance_time_and_run(20)
        self.assertEqual(None, self.machine.game)
        self.assertEqual(0, self.machine.playfield.balls)

    def testBallDoubleDrain(self):
        # prepare game
        self.fill_troughs()
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.ball_saves.default.enabled)

        # start game
        self.start_game()
        self.post_event("enable1")

        self.machine.playfield.add_ball()
        self.advance_time_and_run(4)

        # ball save should be enabled now
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertTrue(self.machine.ball_saves.default.enabled)

        # double drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # game should end
        self.assertEqual(None, self.machine.game)
        self.assertEqual(0, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # first one ball is saved (but will drain soon)
        self.assertEqual(1, self.machine.ball_devices.bd_trough.balls)
        self.advance_time_and_run(10)

    def test_eject_delay(self):
        # prepare game
        self.fill_troughs()
        self.start_game()
        self.post_event("enable4")
        self.advance_time_and_run()
        self.assertBallNumber(1)
        # one ball on pf
        self.assertEqual(1, self.machine.playfield.available_balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # still the same ball
        self.assertBallNumber(1)

        # but no ball on pf
        self.assertEqual(0, self.machine.playfield.available_balls)

        # eject after 10s
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.playfield.available_balls)

    def test_only_last(self):
        # prepare game
        self.fill_troughs()
        self.start_game()
        self.machine.playfield.add_ball(1)
        self.advance_time_and_run(10)
        self.machine.game.balls_in_play = 2

        self.post_event("enable3")
        self.advance_time_and_run()
        self.assertBallNumber(1)
        # two balls on pf
        self.assertEqual(2, self.machine.playfield.available_balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # still the same ball. one ball on pf. no save
        self.assertBallNumber(1)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # last ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # should be safed
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.playfield.available_balls)
        self.assertBallNumber(1)

    def test_unlimited_delay(self):
        # prepare game
        self.fill_troughs()
        self.advance_time_and_run()

        # start game
        self.start_game()
        self.advance_time_and_run(10)
        self.assertBallNumber(1)

        # enable ball save
        self.post_event("enable5")

        # drain ball
        self.drain_all_balls()
        self.advance_time_and_run()

        # ball should not end
        self.assertBallNumber(1)

        # no ball yet on playfield
        self.assertAvailableBallsOnPlayfield(0)

        self.post_event("eject5")
        self.advance_time_and_run()

        # ball 1 continues
        self.assertAvailableBallsOnPlayfield(1)
        self.assertBallNumber(1)

    def test_unlimited_delay_mode(self):
        # prepare game
        self.fill_troughs()
        self.advance_time_and_run()

        # start game
        self.start_game()
        self.advance_time_and_run(10)
        self.assertBallNumber(1)

        # start mode and thereby ball_save
        self.post_event("start_mode2")

        # drain ball
        self.drain_all_balls()
        self.advance_time_and_run()

        # ball should not end
        self.assertBallNumber(1)

        # no ball yet on playfield
        self.assertAvailableBallsOnPlayfield(0)

        self.post_event("mode_ball_save_delayed_eject")
        self.advance_time_and_run()

        # ball 1 continues
        self.assertAvailableBallsOnPlayfield(1)
        self.assertBallNumber(1)

        # save again/drain ball
        self.drain_all_balls()
        self.advance_time_and_run()

        # ball should not end
        self.assertBallNumber(1)

        # no ball yet on playfield
        self.assertAvailableBallsOnPlayfield(0)

        # stop mode
        self.post_event("stop_mode2")
        self.advance_time_and_run()

        # ball 1 continues
        self.assertAvailableBallsOnPlayfield(1)
        self.assertBallNumber(1)

        # ball should end now
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertGameIsNotRunning()
