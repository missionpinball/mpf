"""Test multiball_locks."""
from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestMultiballLock(MpfGameTestCase):

    def getConfigFile(self):
        return self._testMethodName + '.yaml'

    def getMachinePath(self):
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

        lock = self.machine.multiball_locks.lock_no_virtual

        # start mode
        self.post_event("start_no_virtual")

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_no_virtual")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(0, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertEqual(0, lock.locked_balls)

        # lock ejects one ball
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # ball drains
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_no_virtual")
        self.assertPlayerNumber(1)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)

        # it should not keep the ball
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_no_virtual")
        self.assertPlayerNumber(2)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)

        # it should not keep the ball
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # lock a second ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)

        # it should keep two balls
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # game ends
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_all_balls()
        self.drain_all_balls()
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

        lock = self.machine.multiball_locks.lock_virtual_only

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_virtual_only")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(0, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # lock ejects one ball
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # ball drains
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_virtual_only")
        self.assertPlayerNumber(1)
        self.assertEqual(1, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)

        # it should keep the ball
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_virtual_only")
        self.assertPlayerNumber(2)

        # lock stays full
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # game ends
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_all_balls()
        self.drain_all_balls()
        self.advance_time_and_run()

        # game should start again
        self.start_game()

    def testPhysicalOnly(self):
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

        lock = self.machine.multiball_locks.lock_physical_only

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_physical_only")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_physical_only")
        self.assertPlayerNumber(1)

        # look is still full
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)
        # eject a ball
        self.machine.ball_devices.bd_lock.eject()
        self.advance_time_and_run(10)

        # ball is on playfield now
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_physical_only")
        self.assertPlayerNumber(2)

        # only one ball locked. other player stole it
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # game ends
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_all_balls()
        self.drain_all_balls()
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

        lock = self.machine.multiball_locks.lock_min_virtual_physical

        self.advance_time_and_run(4)
        self.assertEqual(0, lock.locked_balls)

        # lock one ball and another one should go to pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # lock ejects one ball
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        # ball drains
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_min_virtual_physical")

        self.assertPlayerNumber(2)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(0, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # steal one ball
        self.machine.ball_devices.bd_lock.eject()
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(1, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_min_virtual_physical")
        self.assertPlayerNumber(1)
        # the other player stole a ball
        self.assertEqual(1, lock.locked_balls)

        # lock one ball
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_lock)
        self.advance_time_and_run(10)

        # it should keep the ball
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)

        # player change
        self.drain_all_balls()
        self.advance_time_and_run(10)

        # start mode
        self.post_event("start_min_virtual_physical")
        self.assertPlayerNumber(2)

        # it should keep the ball
        self.assertEqual(2, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(2, lock.locked_balls)
        # game ends
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertGameIsNotRunning()

        self.assertEqual(0, self.machine.ball_devices.bd_lock.balls)
        self.assertEqual(3, self.machine.playfield.balls)

        # game should not start yet
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        self.drain_all_balls()
        self.drain_all_balls()
        self.drain_all_balls()
        self.advance_time_and_run()

        # game should start again
        self.start_game()