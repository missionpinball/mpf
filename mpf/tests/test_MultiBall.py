"""Test multiballs and multiball_locks."""
from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestMultiBall(MpfGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/multiball/'

    def get_platform(self):
        return 'smart_virtual'

    def testSimpleMultiball(self):
        self.mock_event("multiball_mb1_ended")
        self.mock_event("multiball_mb1_ball_lost")

        # prepare game
        self.fill_troughs()
        self.assertFalse(self.machine.multiballs["mb1"].enabled)

        # start game
        self.start_game()

        # mb1 should not start because its not enabled
        self.post_event("mb1_start")
        self.assertEqual(0, self.machine.multiballs["mb1"].balls_added_live)
        self.assertFalse(self.machine.multiballs["mb1"].enabled)

        self.post_event("mb1_enable")

        # multiball should be enabled now but not started
        self.assertTrue(self.machine.multiballs["mb1"].enabled)
        self.assertEqual(0, self.machine.multiballs["mb1"].balls_added_live)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # ball drains right away
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # multiball not started. game should end
        self.assertEqual(None, self.machine.game)

        # start game again
        self.start_game()
        self.post_event("mb1_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs["mb1"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.post_event("mb1_disable")
        # nothing happens
        self.post_event("mb1_start")
        self.assertEqual(0, self.machine.multiballs["mb1"].balls_added_live)

        # mb start
        self.post_event("mb1_enable")
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs["mb1"].balls_added_live)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertBallsInPlay(2)

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertBallsInPlay(2)

        # two balls drain
        self.drain_one_ball()
        self.drain_one_ball()
        self.assertEqual(0, self._events['multiball_mb1_ended'])

        # they should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEventNotCalled("multiball_mb1_ball_lost")
        self.assertBallsInPlay(2)

        # shoot again ends
        self.advance_time_and_run(10)

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)
        self.assertEventCalled("multiball_mb1_ball_lost", 1)
        self.assertBallsInPlay(1)

        # mb ends
        self.assertEqual(1, self._events['multiball_mb1_ended'])

        # the other ball also drains
        self.drain_one_ball()

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testRestartMultiball(self):
        self.mock_event("multiball_mb1_ended")

        # prepare game
        self.fill_troughs()
        self.assertFalse(self.machine.multiballs["mb1"].enabled)

        # start game
        self.start_game()
        self.post_event("mb1_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs["mb1"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs["mb1"].balls_added_live)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # mb cannot start again/nothing happens
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs["mb1"].balls_added_live)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # shoot again ends
        self.advance_time_and_run(10)

        # mb cannot start again because balls are still in play
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs["mb1"].balls_added_live)
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(0, self._events['multiball_mb1_ended'])

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(0, self.machine.multiballs["mb1"].balls_added_live)
        self.assertEqual(1, self._events['multiball_mb1_ended'])

        # restart mb
        self.post_event("mb1_start")
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.multiballs["mb1"].balls_added_live)
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(40)
        self.assertEqual(2, self.machine.playfield.balls)

        # two balls drains
        self.drain_one_ball()
        self.drain_one_ball()

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(2, self._events['multiball_mb1_ended'])
        self.assertEqual(None, self.machine.game)

    def testUnlimitedShootAgain(self):
        self.mock_event("multiball_mb2_ended")

        # prepare game
        self.fill_troughs()

        # start game
        self.start_game()

        self.post_event("mb2_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs["mb2"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb2_start")
        self.assertEqual(2, self.machine.multiballs["mb2"].balls_added_live)

        # another two balls should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # two balls drain
        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events['multiball_mb2_ended'])

        # they should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # shoot again forever
        self.advance_time_and_run(100)

        # three balls drain
        self.drain_one_ball()
        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.playfield.balls)

        # they should be readded because of shoot again
        self.advance_time_and_run(20)
        self.assertEqual(3, self.machine.playfield.balls)

        # end mb
        self.post_event("mb2_stop")

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # mb does not end yet
        self.assertEqual(0, self._events['multiball_mb2_ended'])

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(1, self._events['multiball_mb2_ended'])

        # the other ball also drains
        self.drain_one_ball()

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testSimultaneousMultiballs(self):
        self.mock_event("multiball_mb2_ended")
        self.mock_event("multiball_mb3_ended")

        # prepare game
        self.fill_troughs()

        # start game
        self.start_game()

        self.post_event("mb2_enable")
        self.post_event("mb3_enable")

        # multiballs should be enabled
        self.assertTrue(self.machine.multiballs["mb2"].enabled)
        self.assertTrue(self.machine.multiballs["mb3"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb2_start")
        self.assertEqual(2, self.machine.multiballs["mb2"].balls_added_live)

        # another two balls should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # start mb3
        self.post_event("mb3_start")
        self.assertEqual(1, self.machine.multiballs["mb3"].balls_added_live)

        # another ball should appear
        self.advance_time_and_run(10)
        self.assertEqual(4, self.machine.playfield.balls)

        self.assertTrue(self.machine.multiballs["mb2"].shoot_again)
        self.assertFalse(self.machine.multiballs["mb3"].shoot_again)

        self.post_event("mb2_stop")
        self.assertFalse(self.machine.multiballs["mb2"].shoot_again)

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(0, self._events['multiball_mb2_ended'])
        self.assertEqual(0, self._events['multiball_mb3_ended'])

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(0, self._events['multiball_mb2_ended'])
        self.assertEqual(0, self._events['multiball_mb3_ended'])

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, self._events['multiball_mb2_ended'])
        self.assertEqual(1, self._events['multiball_mb3_ended'])

        # last ball drains
        self.drain_one_ball()

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballInMode(self):
        self.mock_event("multiball_mb4_ended")

        # prepare game
        self.fill_troughs()

        # start game
        self.start_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mode not loaded. mb4 should not enable or start
        self.post_event("mb4_enable")
        self.post_event("mb4_start")

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # start mode
        self.post_event("start_mode1")

        # mode loaded. mb4 should enable and start
        self.post_event("mb4_enable")
        self.post_event("mb4_start")
        self.assertTrue(self.machine.multiballs["mb4"].enabled)

        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        self.drain_one_ball()
        self.advance_time_and_run(1)

        # it should come back
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(0, self._events['multiball_mb4_ended'])

        # stop mode
        self.post_event("stop_mode1")

        # mode end should stop mp
        self.assertFalse(self.machine.multiballs["mb4"].shoot_again)
        self.assertFalse(self.machine.multiballs["mb4"].enabled)
        self.assertEqual(0, self._events['multiball_mb4_ended'])

        # next drain should end mb
        self.drain_one_ball()
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.playfield.available_balls)
        self.assertEqual(1, self._events['multiball_mb4_ended'])

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballInModeSimple(self):
        self.mock_event("multiball_mb5_ended")

        # prepare game
        self.fill_troughs()

        # start game
        self.start_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # start mode
        self.post_event("start_mode2")

        # mode loaded. mb5 should enabled but not started
        self.assertTrue(self.machine.multiballs["mb5"].enabled)
        self.assertEqual(0, self.machine.multiballs["mb5"].balls_added_live)

        # start it
        self.post_event("mb5_start")
        self.assertEqual(1, self.machine.multiballs["mb5"].balls_added_live)

        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # drain a ball
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # it should come back
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(0, self._events['multiball_mb5_ended'])

        # stop mode
        self.post_event("stop_mode2")

        # mode end should stop mb
        self.assertFalse(self.machine.multiballs["mb5"].shoot_again)
        self.assertFalse(self.machine.multiballs["mb5"].enabled)
        self.assertEqual(0, self._events['multiball_mb5_ended'])

        # next drain should end mb
        self.drain_one_ball()
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.playfield.available_balls)
        self.assertEqual(1, self._events['multiball_mb5_ended'])

        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballWithLock(self):
        # prepare game
        self.fill_troughs()
        self.assertFalse(self.machine.multiballs["mb6"].enabled)

        # start game
        self.start_game()

        # start mode
        self.post_event("start_mode1")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs["mb6"].enabled)
        # lock should be enabled
        self.assertTrue(self.machine.multiball_locks["lock_mb6"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # lock one ball and another one should go to pf
        self.hit_switch_and_run("s_lock1", 10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.game.player_list[0]["lock_mb6_locked_balls"])

        # start mb
        self.post_event("mb6_start")
        self.assertEqual(2, self.machine.multiballs["mb6"].balls_added_live)

        # three balls on pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(0, self.machine.game.player_list[0]["lock_mb6_locked_balls"])

        # game ends (because of slam tilt)
        self.machine.game.end_ball()
        self.advance_time_and_run()

        # this should not crash
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_trough"])
        self.advance_time_and_run()

    def test_total_ball_count(self):
        # prepare game
        self.fill_troughs()
        self.assertFalse(self.machine.multiballs["mb10"].enabled)
        self.assertFalse(self.machine.multiballs["mb11"].enabled)

        # start game
        self.start_game()

        # start mode
        self.post_event("start_mode1")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs["mb10"].enabled)
        self.assertTrue(self.machine.multiballs["mb11"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # start mb10
        self.post_event("mb10_start")
        self.assertEqual(2, self.machine.multiballs["mb10"].balls_added_live)
        self.assertEqual(3, self.machine.multiballs["mb10"].balls_live_target)
        self.assertTrue(self.machine.multiballs["mb10"].shoot_again)

        # three balls on pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # drain one. should come back
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.multiballs["mb10"].balls_added_live)
        self.assertEqual(3, self.machine.multiballs["mb10"].balls_live_target)
        self.assertTrue(self.machine.multiballs["mb10"].shoot_again)

        # no more shoot again
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.multiballs["mb10"].shoot_again)

        # start mb11
        self.post_event("mb11_start")
        self.assertEqual(0, self.machine.multiballs["mb11"].balls_added_live)
        self.assertEqual(2, self.machine.multiballs["mb11"].balls_live_target)
        self.advance_time_and_run(5)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(3, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs["mb11"].shoot_again)

        # drain one. should not come back
        self.drain_one_ball()
        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs["mb11"].shoot_again)

        # but the second one should come back
        self.drain_one_ball()
        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs["mb11"].shoot_again)

        # shoot again ends
        self.advance_time_and_run(10)
        self.assertFalse(self.machine.multiballs["mb10"].shoot_again)
        self.assertFalse(self.machine.multiballs["mb11"].shoot_again)
        self.assertEqual(3, self.machine.multiballs["mb10"].balls_live_target)
        self.assertEqual(2, self.machine.multiballs["mb11"].balls_live_target)
        self.assertEqual(2, self.machine.game.balls_in_play)

        # drain one balls
        self.drain_one_ball()
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.game.balls_in_play)

        # both mbs should end
        self.assertEqual(0, self.machine.multiballs["mb10"].balls_live_target)
        self.assertEqual(0, self.machine.multiballs["mb11"].balls_live_target)

    def test_total_ball_count_with_lock(self):
        # prepare game
        self.fill_troughs()
        self.assertFalse(self.machine.multiballs["mb10"].enabled)
        self.assertFalse(self.machine.multiballs["mb11"].enabled)

        # start game
        self.start_game()

        # start mode
        self.post_event("start_mode1")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs["mb10"].enabled)
        self.assertTrue(self.machine.multiballs["mb11"].enabled)
        # lock should be enabled
        self.assertTrue(self.machine.multiball_locks["lock_mb6"].enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # lock one ball and another one should go to pf
        self.hit_switch_and_run("s_lock1", 10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)

        # start mb10
        self.post_event("mb10_start")
        self.assertEqual(2, self.machine.multiballs["mb10"].balls_added_live)
        self.assertEqual(3, self.machine.multiballs["mb10"].balls_live_target)

        # three balls on pf and one in lock
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)

        # start mb12. eject lock
        self.post_event("mb12_start")
        self.assertEqual(1, self.machine.multiballs["mb12"].balls_added_live)
        self.assertEqual(4, self.machine.multiballs["mb12"].balls_live_target)
        self.advance_time_and_run(5)
        self.assertEqual(4, self.machine.playfield.balls)
        self.assertEqual(4, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs["mb12"].shoot_again)

    def testAddABall(self):
        self.mock_event("multiball_mb_add_a_ball_ended")

        # prepare game
        self.fill_troughs()

        # start game
        self.start_game()

        self.post_event("start_or_add")
        self.advance_time_and_run(10)
        self.assertBallsOnPlayfield(2)

        self.post_event("start_or_add")
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(3)

        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_add_a_ball_ended")

        self.post_event("add_ball")
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(3)

        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_add_a_ball_ended")

        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(1)
        self.assertEventCalled("multiball_mb_add_a_ball_ended")

        self.post_event("add_ball")
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(1)

    def testMultiballLockFullMultiplayer(self):
        self.machine.config['game']['balls_per_game'] = self.machine.placeholder_manager.build_int_template(3)
        self.mock_event("multiball_lock_lock_mb6_full")
        self.fill_troughs()
        self.start_two_player_game()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.post_event("start_mode1")

        # lock ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(5)

        # machine should request a new ball and the lock keeps one
        self.assertEqual(1, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(0, self.machine.game.player_list[1]["lock_mb6_locked_balls"])
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(4, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        # drain ball. player 2 should be up
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.post_event("start_mode1")
        self.assertPlayerNumber(2)
        self.assertBallNumber(1)

        # also lock a ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(5)

        # lock should not keep the ball but count it for the player
        self.assertEqual(1, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(1, self.machine.game.player_list[1]["lock_mb6_locked_balls"])
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(4, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)
        self.assertEventNotCalled("multiball_lock_lock_mb6_full")

        # lock another ball. lock should keep it
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(5)
        self.assertEqual(1, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(2, self.machine.game.player_list[1]["lock_mb6_locked_balls"])
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(3, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)
        self.assertEventCalled("multiball_lock_lock_mb6_full")

        # drain ball. lock should release a ball because player1 need to be able to complete it
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertEqual(1, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(2, self.machine.game.player_list[1]["lock_mb6_locked_balls"])
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(4, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(0)

        # ball from lock drains
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(4, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        self.post_event("start_mode1")

        # lock another ball. lock should keep it
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(5)
        self.assertEqual(2, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(2, self.machine.game.player_list[1]["lock_mb6_locked_balls"])
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(3, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        # start MB
        self.post_event("mb6_start")
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(3)
        self.assertBallsInPlay(3)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(3, self.machine.ball_devices["bd_trough"].balls)

        # drain ball
        self.drain_one_ball()
        self.advance_time_and_run()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.assertBallsOnPlayfield(2)
        self.assertBallsInPlay(2)

        # drain ball
        self.drain_one_ball()
        self.advance_time_and_run()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        # drain ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.post_event("start_mode1")
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(5, self.machine.ball_devices["bd_trough"].balls)
        self.assertEqual(0, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(2, self.machine.game.player_list[1]["lock_mb6_locked_balls"])

        # start mb without balls in lock
        self.post_event("mb6_start")
        self.advance_time_and_run(15)
        self.assertBallsOnPlayfield(3)
        self.assertBallsInPlay(3)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(3, self.machine.ball_devices["bd_trough"].balls)

        self.assertEqual(0, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(0, self.machine.game.player_list[1]["lock_mb6_locked_balls"])

        # drain ball
        self.drain_one_ball()
        self.advance_time_and_run()
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)
        self.assertBallsOnPlayfield(2)
        self.assertBallsInPlay(2)

        # drain ball
        self.drain_one_ball()
        self.advance_time_and_run()
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)
        self.assertBallsOnPlayfield(1)
        self.assertBallsInPlay(1)

        # drain last ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.post_event("start_mode1")
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(5, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsInPlay(1)

        # lock ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(5)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(4, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsInPlay(1)

        # drain again
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        self.assertEqual(1, self.machine.game.player_list[0]["lock_mb6_locked_balls"])
        self.assertEqual(0, self.machine.game.player_list[1]["lock_mb6_locked_balls"])

        # drain again. game should end
        self.drain_one_ball()

        # lock should eject all balls
        self.advance_time_and_run(5)
        self.assertGameIsNotRunning()
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(5, self.machine.ball_devices["bd_trough"].balls)
        self.assertBallsOnPlayfield(1)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        # ball from lock drain
        self.drain_one_ball()
        self.advance_time_and_run()

        # start new game
        self.start_game()
        self.post_event("start_mode1")

        self.drain_one_ball()
        self.advance_time_and_run()

    def testModeWithMultiballAutostart(self):
        # prepare game
        self.fill_troughs()

        # start game
        self.start_game()
        self.post_event("start_mode3")
        self.advance_time_and_run(1)

        # multiball should be enabled now but not started
        self.assertTrue(self.machine.multiballs["mb_autostart"].enabled)
        self.assertEqual(1, self.machine.multiballs["mb_autostart"].balls_added_live)

    def testMultiballWhichStartsAfterLock(self):
        self.mock_event("multiball_mb_autostart_ended")
        self.mock_event("multiball_mb_autostart_ball_lost")

        # prepare game
        self.fill_troughs()
        self.assertFalse(self.machine.multiballs["mb4_autostart"].enabled)

        # start game
        self.start_game()

        # start mode
        self.post_event("start_mode4")
        self.advance_time_and_run(5)

        self.assertAvailableBallsOnPlayfield(1)
        self.assertEqual(5, self.machine.ball_devices["bd_trough"].available_balls)

        # multiball should be enabled now but not started
        self.assertTrue(self.machine.multiballs["mb4_autostart"].enabled)
        self.assertEqual(0, self.machine.multiballs["mb4_autostart"].balls_added_live)

        # lock a ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(1)

        # mb should start
        self.assertTrue(self.machine.multiballs["mb4_autostart"].enabled)
        self.assertEqual(1, self.machine.multiballs["mb4_autostart"].balls_added_live)
        self.assertBallsInPlay(2)
        self.assertAvailableBallsOnPlayfield(2)

        # lock should eject
        self.assertEqual(4, self.machine.ball_devices["bd_trough"].available_balls)
        self.assertEqual(0, self.machine.ball_devices["bd_lock"].available_balls)

        # both balls drain
        self.drain_all_balls()

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballStateInPlaceholder(self):
        self.fill_troughs()
        self.start_game()

        self.post_event("start_default")
        self.mock_event("should_post_when_enabled")
        self.mock_event("should_post_when_disabled")
        self.mock_event("should_not_post_when_enabled")
        self.mock_event("should_not_post_when_disabled")
        mb = self.machine.multiballs["mb1"]

        self.assertFalse(mb.enabled)
        self.post_event("test_event_when_disabled")
        self.assertEventCalled("should_post_when_disabled")
        self.assertEventNotCalled("should_not_post_when_disabled")

        mb.enable()
        self.assertTrue(mb.enabled)
        self.post_event("test_event_when_enabled")
        self.assertEventCalled("should_post_when_enabled")
        self.assertEventNotCalled("should_not_post_when_enabled")

    def testShootAgainPlaceholder(self):
        self.fill_troughs()
        self.start_game()
        self.assertAvailableBallsOnPlayfield(1)

        # start mb with no shoot again set in machine var
        self.mock_event("multiball_mb_placeholder_shoot_again_ended")
        self.mock_event("multiball_mb_placeholder_ended")
        self.post_event("mb_placeholder_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)
        # shoot again should end instantly
        self.assertEventCalled("multiball_mb_placeholder_shoot_again_ended")

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(1)
        # mb should end
        self.assertEventCalled("multiball_mb_placeholder_ended")

        # set shoot again time
        self.machine.variables.set_machine_var("shoot_again_sec", 30)
        # start mb again
        self.mock_event("multiball_mb_placeholder_shoot_again_ended")
        self.mock_event("multiball_mb_placeholder_ended")
        self.post_event("mb_placeholder_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)
        # shoot again should not end instantly
        self.assertEventNotCalled("multiball_mb_placeholder_shoot_again_ended")

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        # shoot again should bring it back
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_placeholder_ended")

        # wait 30s for shoot again to end
        self.advance_time_and_run(30)
        self.assertEventCalled("multiball_mb_placeholder_shoot_again_ended")

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(1)
        # mb should end
        self.assertEventCalled("multiball_mb_placeholder_ended")

    def testShootAgainHurryUpAndGracePeriod(self):
        self.fill_troughs()
        self.start_game()
        self.assertAvailableBallsOnPlayfield(1)
        self.mock_event("multiball_mb_alltimers_ended")
        self.mock_event("multiball_mb_alltimers_shoot_again_ended")
        self.mock_event("multiball_mb_alltimers_grace_period")
        self.mock_event("multiball_mb_alltimers_hurry_up")

        # start mb 30s shoot again, 10s hurry up, 5s grace
        self.post_event("mb_alltimers_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        # shoot again should bring it back
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_alltimers_ended")
        self.assertEventNotCalled("multiball_mb_alltimers_shoot_again_ended")
        self.assertEventNotCalled("multiball_mb_alltimers_grace_period")
        self.assertEventNotCalled("multiball_mb_alltimers_hurry_up")

        #advance time to hurry up
        self.advance_time_and_run(10)
        self.assertEventCalled("multiball_mb_alltimers_hurry_up")
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_alltimers_ended")
        self.assertEventNotCalled("multiball_mb_alltimers_shoot_again_ended")
        self.assertEventNotCalled("multiball_mb_alltimers_grace_period")

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        # shoot again should bring it back
        self.assertAvailableBallsOnPlayfield(2)

        # wait 7s for shoot again to end, but within grace period
        self.advance_time_and_run(7)
        self.assertEventCalled("multiball_mb_alltimers_grace_period")
        self.assertEventNotCalled("multiball_mb_alltimers_ended")
        self.assertEventNotCalled("multiball_mb_alltimers_shoot_again_ended")

        # drain one ball after grace period has ended
        self.advance_time_and_run(5)
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(1)
        # mb should end
        self.assertEventCalled("multiball_mb_alltimers_ended")

    def testShootAgainModeEnd(self):
        self.fill_troughs()
        self.start_game()
        self.assertAvailableBallsOnPlayfield(1)
        self.mock_event("multiball_mb_mode5_ended")
        self.mock_event("multiball_mb_mode5_shoot_again_ended")
        self.mock_event("multiball_mb_mode5_grace_period")
        self.mock_event("multiball_mb_mode5_hurry_up")

        #start Mode5
        self.post_event("start_mode5")

        # start mb 30s shoot again, 10s hurry up, 5s grace
        self.post_event("mb_mode5_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_mode5_ended")
        self.assertEventNotCalled("multiball_mb_mode5_shoot_again_ended")
        self.assertEventNotCalled("multiball_mb_mode5_grace_period")
        self.assertEventNotCalled("multiball_mb_mode5_hurry_up")

        #stop Mode5
        self.post_event("stop_mode5")
        self.advance_time_and_run(5)
        self.assertEventNotCalled("multiball_mb_mode5_ended")
        self.assertEventCalled("multiball_mb_mode5_shoot_again_ended")
        self.assertEventCalled("multiball_mb_mode5_grace_period")
        self.assertEventCalled("multiball_mb_mode5_hurry_up")

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        # shoot again should not bring it back
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEventCalled("multiball_mb_mode5_ended")

    def testShootAgainModeEndNoGracePeriodOrHurryUp(self):
        self.fill_troughs()
        self.start_game()
        self.assertAvailableBallsOnPlayfield(1)
        self.mock_event("multiball_mb_mode5_lean_ended")
        self.mock_event("multiball_mb_mode5_lean_shoot_again_ended")
        self.mock_event("multiball_mb_mode5_lean_grace_period")
        self.mock_event("multiball_mb_mode5_lean_hurry_up")

        #start Mode5
        self.post_event("start_mode5")

        # start mb 30s shoot again
        self.post_event("mb_mode5_lean_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventNotCalled("multiball_mb_mode5_lean_ended")
        self.assertEventNotCalled("multiball_mb_mode5_lean_shoot_again_ended")
        self.assertEventNotCalled("multiball_mb_mode5_lean_grace_period")
        self.assertEventNotCalled("multiball_mb_mode5_lean_hurry_up")

        #stop Mode5
        self.post_event("stop_mode5")
        self.advance_time_and_run(5)
        self.assertEventNotCalled("multiball_mb_mode5_lean_ended")
        self.assertEventCalled("multiball_mb_mode5_lean_shoot_again_ended")
        self.assertEventNotCalled("multiball_mb_mode5_lean_grace_period")
        self.assertEventNotCalled("multiball_mb_mode5_lean_hurry_up")

        # drain one ball
        self.drain_one_ball()
        self.advance_time_and_run(5)
        # shoot again should not bring it back
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEventCalled("multiball_mb_mode5_lean_ended")
        self.assertEventNotCalled("multiball_mb_mode5_lean_grace_period")
        self.assertEventNotCalled("multiball_mb_mode5_lean_hurry_up")

    def testAddABallSaver(self):
        self.fill_troughs()
        self.start_game()
        self.assertAvailableBallsOnPlayfield(1)
        self.mock_event("multiball_mb_add_a_ball_timers_ended")
        self.mock_event("multiball_mb_add_a_ball_timers_shoot_again_ended")
        self.mock_event("multiball_mb_add_a_ball_timers_grace_period")
        self.mock_event("multiball_mb_add_a_ball_timers_hurry_up")
        self.mock_event("ball_save_mb_add_a_ball_timers_timer_start")
        self.mock_event("ball_save_mb_add_a_ball_timers_add_a_ball_timer_start")

        # start mb 30s shoot again, 10s hurry up, 5s grace
        self.post_event("mb_add_a_ball_timers_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventCalled("ball_save_mb_add_a_ball_timers_timer_start")

        # end ball save
        self.advance_time_and_run(35)
        self.assertEventCalled("multiball_mb_add_a_ball_timers_shoot_again_ended")

        #add a ball - ball save 20, hurry up 5, grace 10
        self.post_event("add_ball")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(3)
        self.assertEventCalled("ball_save_mb_add_a_ball_timers_timer_start",1)
        self.assertEventCalled("ball_save_mb_add_a_ball_timers_add_a_ball_timer_start")
        self.assertEventNotCalled("multiball_mb_add_a_ball_timers_ended")
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(3)

        #hurry up
        self.advance_time_and_run(7)
        self.assertEventCalled("multiball_mb_add_a_ball_timers_hurry_up")
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(3)
        #grace period
        self.assertEventCalled("multiball_mb_add_a_ball_timers_grace_period")
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertAvailableBallsOnPlayfield(3)
        self.assertEventCalled("multiball_mb_add_a_ball_timers_shoot_again_ended")

        #drain out and mb should end
        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run(5)
        self.assertEventCalled("multiball_mb_add_a_ball_timers_ended")

    def testAddABallSaverDuringShootAgain(self):
        self.fill_troughs()
        self.start_game()
        self.assertAvailableBallsOnPlayfield(1)
        self.mock_event("ball_save_mb_add_a_ball_timers_timer_start")
        self.mock_event("ball_save_mb_add_a_ball_timers_add_a_ball_timer_start")

        # start mb 30s shoot again, 10s hurry up, 5s grace
        self.post_event("mb_add_a_ball_timers_start")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(2)
        self.assertEventCalled("ball_save_mb_add_a_ball_timers_timer_start")
        # add a ball
        self.post_event("add_ball")
        self.advance_time_and_run(5)
        self.assertAvailableBallsOnPlayfield(3)
        self.assertEventCalled("ball_save_mb_add_a_ball_timers_timer_start", 1)
        self.assertEventNotCalled("ball_save_mb_add_a_ball_timers_add_a_ball_timer_start")
