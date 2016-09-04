from mpf.tests.MpfTestCase import MpfTestCase


class TestMultiBall(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/multiball/'

    def get_platform(self):
        return 'smart_virtual'

    def testSimpleMultiball(self):
        self.mock_event("multiball_mb1_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.multiballs.mb1.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # mb1 should not start because its not enabled
        self.post_event("mb1_start")
        self.assertEqual(0, self.machine.multiballs.mb1.balls_added_live)
        self.assertFalse(self.machine.multiballs.mb1.enabled)

        self.post_event("mb1_enable")

        # multiball should be enabled now but not started
        self.assertTrue(self.machine.multiballs.mb1.enabled)
        self.assertEqual(0, self.machine.multiballs.mb1.balls_added_live)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # ball drains right away
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # multiball not started. game should end
        self.assertEqual(None, self.machine.game)

        # start game again
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()
        self.post_event("mb1_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb1.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.post_event("mb1_disable")
        # nothing happens
        self.post_event("mb1_start")
        self.assertEqual(0, self.machine.multiballs.mb1.balls_added_live)

        # mb start
        self.post_event("mb1_enable")
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs.mb1.balls_added_live)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # two balls drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events['multiball_mb1_ended'])

        # they should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # shoot again ends
        self.advance_time_and_run(10)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(1, self._events['multiball_mb1_ended'])

        # the other ball also drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testRestartMultiball(self):
        self.mock_event("multiball_mb1_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.multiballs.mb1.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()
        self.post_event("mb1_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb1.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs.mb1.balls_added_live)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
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
        self.assertEqual(1, self.machine.multiballs.mb1.balls_added_live)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # shoot again ends
        self.advance_time_and_run(10)

        # mb cannot start again because balls are still in play
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs.mb1.balls_added_live)
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(0, self._events['multiball_mb1_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(0, self.machine.multiballs.mb1.balls_added_live)
        self.assertEqual(1, self._events['multiball_mb1_ended'])

        # restart mb
        self.post_event("mb1_start")
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.multiballs.mb1.balls_added_live)
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(40)
        self.assertEqual(2, self.machine.playfield.balls)

        # two balls drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(2, self._events['multiball_mb1_ended'])
        self.assertEqual(None, self.machine.game)

    def testUnlimitedShootAgain(self):
        self.mock_event("multiball_mb2_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        self.post_event("mb2_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb2.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb2_start")
        self.assertEqual(2, self.machine.multiballs.mb2.balls_added_live)

        # another two balls should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # two balls drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events['multiball_mb2_ended'])

        # they should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # shoot again forever
        self.advance_time_and_run(100)

        # three balls drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.playfield.balls)

        # they should be readded because of shoot again
        self.advance_time_and_run(20)
        self.assertEqual(3, self.machine.playfield.balls)

        # end mb
        self.post_event("mb2_stop")

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # mb does not end yet
        self.assertEqual(0, self._events['multiball_mb2_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(1, self._events['multiball_mb2_ended'])

        # the other ball also drains
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testSimultaneousMultiballs(self):
        self.mock_event("multiball_mb2_ended")
        self.mock_event("multiball_mb3_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        self.post_event("mb2_enable")
        self.post_event("mb3_enable")

        # multiballs should be enabled
        self.assertTrue(self.machine.multiballs.mb2.enabled)
        self.assertTrue(self.machine.multiballs.mb3.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb2_start")
        self.assertEqual(2, self.machine.multiballs.mb2.balls_added_live)

        # another two balls should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # start mb3
        self.post_event("mb3_start")
        self.assertEqual(1, self.machine.multiballs.mb3.balls_added_live)

        # another ball should appear
        self.advance_time_and_run(10)
        self.assertEqual(4, self.machine.playfield.balls)

        self.assertTrue(self.machine.multiballs.mb2.shoot_again)
        self.assertFalse(self.machine.multiballs.mb3.shoot_again)

        self.post_event("mb2_stop")
        self.assertFalse(self.machine.multiballs.mb2.shoot_again)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(0, self._events['multiball_mb2_ended'])
        self.assertEqual(0, self._events['multiball_mb3_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(0, self._events['multiball_mb2_ended'])
        self.assertEqual(0, self._events['multiball_mb3_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, self._events['multiball_mb2_ended'])
        self.assertEqual(1, self._events['multiball_mb3_ended'])

        # last ball drains
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballInMode(self):
        self.mock_event("multiball_mb4_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

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
        self.assertTrue(self.machine.multiballs.mb4.enabled)

        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # it should come back
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(0, self._events['multiball_mb4_ended'])

        # stop mode
        self.post_event("stop_mode1")

        # mode end should stop mp
        self.assertFalse(self.machine.multiballs.mb4.shoot_again)
        self.assertFalse(self.machine.multiballs.mb4.enabled)
        self.assertEqual(0, self._events['multiball_mb4_ended'])

        # next drain should end mb
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.playfield.available_balls)
        self.assertEqual(1, self._events['multiball_mb4_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballInModeSimple(self):
        self.mock_event("multiball_mb5_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # start mode
        self.post_event("start_mode2")

        # mode loaded. mb5 should enabled but not started
        self.assertTrue(self.machine.multiballs.mb5.enabled)
        self.assertEqual(0, self.machine.multiballs.mb5.balls_added_live)

        # start it
        self.post_event("mb5_start")
        self.assertEqual(1, self.machine.multiballs.mb5.balls_added_live)

        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.available_balls)

        # drain a ball
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # it should come back
        self.assertEqual(2, self.machine.playfield.available_balls)
        self.assertEqual(0, self._events['multiball_mb5_ended'])

        # stop mode
        self.post_event("stop_mode2")

        # mode end should stop mb
        self.assertFalse(self.machine.multiballs.mb5.shoot_again)
        self.assertFalse(self.machine.multiballs.mb5.enabled)
        self.assertEqual(0, self._events['multiball_mb5_ended'])

        # next drain should end mb
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.playfield.available_balls)
        self.assertEqual(1, self._events['multiball_mb5_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testMultiballWithLock(self):
        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.multiballs.mb6.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb6.enabled)
        # lock should be enabled
        self.assertTrue(self.machine.ball_locks.lock_mb6.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # lock one ball and another one should go to pf
        self.hit_switch_and_run("s_lock1", 10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)

        # start mb
        self.post_event("mb6_start")
        self.assertEqual(2, self.machine.multiballs.mb6.balls_added_live)

        # three balls on pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(0, self.machine.ball_devices.bd_lock.balls)

    def test_total_ball_count(self):
        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.multiballs.mb10.enabled)
        self.assertFalse(self.machine.multiballs.mb11.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb10.enabled)
        self.assertTrue(self.machine.multiballs.mb11.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # start mb10
        self.post_event("mb10_start")
        self.assertEqual(2, self.machine.multiballs.mb10.balls_added_live)
        self.assertEqual(3, self.machine.multiballs.mb10.balls_live_target)
        self.assertTrue(self.machine.multiballs.mb10.shoot_again)

        # three balls on pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # drain one. should come back
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(5)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.multiballs.mb10.balls_added_live)
        self.assertEqual(3, self.machine.multiballs.mb10.balls_live_target)
        self.assertTrue(self.machine.multiballs.mb10.shoot_again)

        # no more shoot again
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.multiballs.mb10.shoot_again)

        # start mb11
        self.post_event("mb11_start")
        self.assertEqual(0, self.machine.multiballs.mb11.balls_added_live)
        self.assertEqual(2, self.machine.multiballs.mb11.balls_live_target)
        self.advance_time_and_run(5)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(3, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs.mb11.shoot_again)

        # drain one. should not come back
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs.mb11.shoot_again)

        # but the second one should come back
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(4)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs.mb11.shoot_again)

        # shoot again ends
        self.advance_time_and_run(10)
        self.assertFalse(self.machine.multiballs.mb10.shoot_again)
        self.assertFalse(self.machine.multiballs.mb11.shoot_again)
        self.assertEqual(3, self.machine.multiballs.mb10.balls_live_target)
        self.assertEqual(2, self.machine.multiballs.mb11.balls_live_target)
        self.assertEqual(2, self.machine.game.balls_in_play)

        # drain one balls
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.game.balls_in_play)

        # both mbs should end
        self.assertEqual(0, self.machine.multiballs.mb10.balls_live_target)
        self.assertEqual(0, self.machine.multiballs.mb11.balls_live_target)

    def test_total_ball_count_with_lock(self):
        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.multiballs.mb10.enabled)
        self.assertFalse(self.machine.multiballs.mb11.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb10.enabled)
        self.assertTrue(self.machine.multiballs.mb11.enabled)
        # lock should be enabled
        self.assertTrue(self.machine.ball_locks.lock_mb6.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # lock one ball and another one should go to pf
        self.hit_switch_and_run("s_lock1", 10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)

        # start mb10
        self.post_event("mb10_start")
        self.assertEqual(2, self.machine.multiballs.mb10.balls_added_live)
        self.assertEqual(3, self.machine.multiballs.mb10.balls_live_target)

        # three balls on pf and one in lock
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)

        # start mb11. eject lock
        self.post_event("mb11_start")
        self.assertEqual(1, self.machine.multiballs.mb11.balls_added_live)
        self.assertEqual(2, self.machine.multiballs.mb11.balls_live_target)
        self.advance_time_and_run(5)
        self.assertEqual(4, self.machine.playfield.balls)
        self.assertEqual(4, self.machine.game.balls_in_play)
        self.assertTrue(self.machine.multiballs.mb11.shoot_again)
