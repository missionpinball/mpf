"""Test multiball_locks."""
from mpf.tests.MpfGameTestCase import MpfGameTestCase
from mpf.tests.MpfTestCase import test_config


class TestMultiballLock(MpfGameTestCase):
    def get_config_file(self):
        return 'testDefault.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/multiball_locks/'

    def get_platform(self):
        return 'smart_virtual'

    @test_config("testSourceDevices.yaml")
    def test_source_devices(self):
        self.fill_troughs()
        self.start_game()
        self.post_event("start_source_devices")
        self.assertModeRunning("source_devices")

        lock_device = self.machine.ball_devices["bd_lock_triple"]
        lock_device2 = self.machine.ball_devices["bd_lock"]
        self.machine.default_platform.add_ball_to_device(lock_device)
        self.advance_time_and_run(10)
        self.assertEqual(1, lock_device.balls)
        self.assertEqual(0, lock_device2.balls)
        self.assertBallsInPlay(1)
        self.assertBallsOnPlayfield(1)

        self.machine.default_platform.add_ball_to_device(lock_device2)
        self.advance_time_and_run(10)
        self.assertEqual(0, lock_device.balls)
        self.assertEqual(1, lock_device2.balls)
        self.assertBallsInPlay(1)
        self.assertBallsOnPlayfield(1)

        self.machine.default_platform.add_ball_to_device(lock_device2)
        self.advance_time_and_run(10)
        self.assertEqual(0, lock_device.balls)
        self.assertEqual(2, lock_device2.balls)
        self.assertBallsInPlay(1)
        self.assertBallsOnPlayfield(1)

    def test_filling_two(self):
        self.fill_troughs()
        self.start_game()
        self.mock_event("multiball_lock_lock_default_locked_ball")
        self.mock_event("multiball_lock_lock_default_full")
        self.post_event("start_default")

        lock_device = self.machine.ball_devices["bd_lock"]
        mb_lock = self.machine.multiball_locks["lock_default"]

        # Add one ball, should lock but not be full
        self.machine.default_platform.add_ball_to_device(lock_device)
        self.advance_time_and_run(10)
        self.assertEqual(1, lock_device.balls)
        self.assertEqual(1, mb_lock.locked_balls)
        self.assertEventCalled("multiball_lock_lock_default_locked_ball")
        self.assertEqual({'total_balls_locked': 1},
                         self._last_event_kwargs["multiball_lock_lock_default_locked_ball"])
        self.assertEventNotCalled("multiball_lock_lock_default_full")

        # Add a second ball, should lock and be full
        self.machine.default_platform.add_ball_to_device(lock_device)
        self.advance_time_and_run(10)
        self.assertEqual(2, lock_device.balls)
        self.assertEqual(2, mb_lock.locked_balls)
        self.assertEventCalled("multiball_lock_lock_default_locked_ball")
        self.assertEqual({'total_balls_locked': 2},
                         self._last_event_kwargs["multiball_lock_lock_default_locked_ball"])
        self.assertEventCalledWith("multiball_lock_lock_default_full", balls=2)

    def test_filling_three(self):
        self.fill_troughs()
        self.start_game()
        self.mock_event("multiball_lock_lock_triple_locked_ball")
        self.mock_event("multiball_lock_lock_triple_full")
        self.post_event("start_default")

        lock_device_3 = self.machine.ball_devices["bd_lock_triple"]
        mb_lock_3 = self.machine.multiball_locks["lock_triple"]

        # Add one ball, should lock but not be full
        self.machine.default_platform.add_ball_to_device(lock_device_3)
        self.advance_time_and_run(10)
        self.assertEqual(1, lock_device_3.balls)
        self.assertEqual(1, mb_lock_3.locked_balls)
        self.assertEventCalled("multiball_lock_lock_triple_locked_ball")
        self.assertEqual({'total_balls_locked': 1},
                         self._last_event_kwargs["multiball_lock_lock_triple_locked_ball"])
        self.assertEventNotCalled("multiball_lock_lock_triple_full")

        # Add a second ball, should lock but not be full
        self.machine.default_platform.add_ball_to_device(lock_device_3)
        self.advance_time_and_run(10)
        self.assertEqual(2, lock_device_3.balls)
        self.assertEqual(2, mb_lock_3.locked_balls)
        self.assertEventCalled("multiball_lock_lock_triple_locked_ball")
        self.assertEqual({'total_balls_locked': 2},
                         self._last_event_kwargs["multiball_lock_lock_triple_locked_ball"])
        self.assertEventNotCalled("multiball_lock_lock_triple_full")

        # Add a third ball, should lock but not be full
        self.machine.default_platform.add_ball_to_device(lock_device_3)
        self.advance_time_and_run(10)
        self.assertEqual(3, lock_device_3.balls)
        self.assertEqual(3, mb_lock_3.locked_balls)
        self.assertEventCalled("multiball_lock_lock_triple_locked_ball")
        self.assertEqual({'total_balls_locked': 3},
                         self._last_event_kwargs["multiball_lock_lock_triple_locked_ball"])
        self.assertEventCalledWith("multiball_lock_lock_triple_full", balls=3)

    def test_placeholder_events(self):
        self.fill_troughs()
        self.start_game()

        self.post_event("start_default")
        self.mock_event("should_post_when_enabled")
        self.mock_event("should_post_when_disabled")
        self.mock_event("should_not_post_when_enabled")
        self.mock_event("should_not_post_when_disabled")
        lock = self.machine.multiball_locks["lock_default"]

        self.assertTrue(lock.enabled)
        self.assertPlaceholderEvaluates(True, "device.multiball_locks.lock_default.enabled")
        self.post_event("test_event_when_enabled")
        self.assertEventCalled("should_post_when_enabled")
        self.assertEventNotCalled("should_not_post_when_enabled")

        lock.disable()
        self.assertFalse(lock.enabled)
        self.assertPlaceholderEvaluates(False, "device.multiball_locks.lock_default.enabled")
        self.post_event("test_event_when_disabled")
        self.assertEventCalled("should_post_when_disabled")
        self.assertEventNotCalled("should_not_post_when_disabled")


class TestMultiballLockCountingStrategies(MpfGameTestCase):

    def get_config_file(self):
        return self._testMethodName + '.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/multiball_locks/'

    def get_platform(self):
        return 'smart_virtual'

    def testNoVirtual(self):
        # prepare game
        self.fill_troughs()

        # start game
        self.start_two_player_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        lock = self.machine.multiball_locks["lock_no_virtual"]

        # start mode
        self.post_event("start_no_virtual")

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_no_virtual")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(0, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertEqual(0, lock.locked_balls)

        # lock ejects one ball
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_no_virtual")
        self.assertPlayerNumber(1)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)

        # it should not keep the ball
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_no_virtual")
        self.assertPlayerNumber(2)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)

        # it should not keep the ball
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # lock a second ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)

        # it should keep two balls
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # game ends
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run()

        # game should start again
        self.start_game()

    def testVirtualOnly(self):
        # prepare game
        self.fill_troughs()

        # start game
        self.start_two_player_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # start mode
        self.post_event("start_virtual_only")

        lock = self.machine.multiball_locks["lock_virtual_only"]

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_virtual_only")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(0, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # lock ejects one ball
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_virtual_only")
        self.assertPlayerNumber(1)
        self.assertEqual(1, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)

        # it should keep the ball
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_virtual_only")
        self.assertPlayerNumber(2)

        # lock stays full
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # game ends
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run()

        # game should start again
        self.start_game()

    def testPhysicalOnly(self):
        self.mock_event("multiball_lock_lock_physical_only_locked_ball")
        self.mock_event("multiball_lock_lock_physical_only_full")
        # prepare game
        self.fill_troughs()

        # start game
        self.start_two_player_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # start mode
        self.post_event("start_physical_only")

        self.mock_event("multiball_lock_lock_physical_only_smaller_than_device_locked_ball")
        self.mock_event("multiball_lock_lock_physical_only_smaller_than_device_full")
        lock2 = self.machine.multiball_locks["lock_physical_only_smaller_than_device"]
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock_triple"])
        self.advance_time_and_run(10)

        self.assertEqual(1, self.machine.ball_devices["bd_lock_triple"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock2.locked_balls)
        self.assertEventNotCalled("multiball_lock_lock_physical_only_smaller_than_device_full")
        self.assertEventCalled("multiball_lock_lock_physical_only_smaller_than_device_locked_ball", times=1)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock_triple"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock_triple"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock2.locked_balls)
        self.assertEventCalled("multiball_lock_lock_physical_only_smaller_than_device_full")
        self.assertEventCalled("multiball_lock_lock_physical_only_smaller_than_device_locked_ball", times=2)

        self.mock_event("multiball_lock_lock_physical_only_smaller_than_device_full")
        self.mock_event("multiball_lock_lock_physical_only_smaller_than_device_locked_ball")
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock_triple"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock_triple"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock2.locked_balls)
        self.assertEventNotCalled("multiball_lock_lock_physical_only_smaller_than_device_full")
        self.assertEventNotCalled("multiball_lock_lock_physical_only_smaller_than_device_locked_ball")

        lock = self.machine.multiball_locks["lock_physical_only"]

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)
        self.assertEventCalledWith("multiball_lock_lock_physical_only_locked_ball", total_balls_locked=1)
        self.assertEventNotCalled("multiball_lock_lock_physical_only_full")

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.mock_event("multiball_lock_lock_physical_only_locked_ball")
        self.post_event("start_physical_only")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)
        self.assertEventCalledWith("multiball_lock_lock_physical_only_locked_ball", total_balls_locked=2)
        self.assertEventCalledWith("multiball_lock_lock_physical_only_full", balls=2)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_physical_only")
        self.assertPlayerNumber(1)

        # look is still full
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)
        # eject a ball
        self.machine.ball_devices["bd_lock"].eject()
        self.advance_time_and_run(10)

        # ball is on playfield now
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_physical_only")
        self.assertPlayerNumber(2)

        # only one ball locked. other player stole it
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # game ends
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(4, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_one_ball()
        self.drain_one_ball()
        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run()

        # game should start again
        self.start_game()

    def testMinVirtualPhysical(self):
        # prepare game
        self.fill_troughs()

        # start game
        self.start_two_player_game()

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        self.advance_time_and_run(4)
        self.assertEqual(1, self.machine.playfield.available_balls)

        # start mode
        self.post_event("start_min_virtual_physical")

        lock = self.machine.multiball_locks["lock_min_virtual_physical"]

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # lock ejects one ball
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # ball drains
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_min_virtual_physical")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(0, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # steal one ball
        self.machine.ball_devices["bd_lock"].eject()
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_min_virtual_physical")
        self.assertPlayerNumber(1)
        # the other player stole a ball
        self.assertEqual(1, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_lock"])
        self.advance_time_and_run(10)

        # it should keep the ball
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_one_ball()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_min_virtual_physical")
        self.assertPlayerNumber(2)

        # it should keep the ball
        self.assertEqual(2, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)
        # game ends
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices["bd_lock"].balls)
        self.assertEqual(3, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_one_ball()
        self.drain_one_ball()
        self.drain_one_ball()
        self.advance_time_and_run()

        # game should start again
        self.start_game()
