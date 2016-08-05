# TODO: test remaining actions
# TODO: test empty control_events

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestModeTimer(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'test_mode_timers.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mode_tests/'

    def _mode_timer_start(self, **kwargs):
        del kwargs
        self.started = True

    def _mode_timer_tick(self, **kwargs):
        del kwargs
        self.tick += 1

    def _mode_timer_complete(self, **kwargs):
        del kwargs
        self.started = False

    def test_start_with_game(self):
        self.start_game()
        self.advance_time_and_run()
        self.assertIn(self.machine.modes.mode_with_timers2,
                      self.machine.mode_controller.active_modes)

        self.assertIn(self.machine.modes.game,
                      self.machine.mode_controller.active_modes)

    def test_mode_timer_down_with_player(self):
        self.machine.events.add_handler("timer_timer_down_tick", self._mode_timer_tick)
        self.machine.events.add_handler("timer_timer_down_started", self._mode_timer_start)
        self.machine.events.add_handler("timer_timer_down_complete", self._mode_timer_complete)
        self.machine.events.add_handler("timer_timer_down_stopped", self._mode_timer_complete)

        # add a fake player
        player = {}
        self.machine.mode_controller._player_turn_start(player)

        self.assertFalse(self.machine.modes.mode_with_timers.active)

        self.tick = 0
        self.started = False

        # timer should not start when mode is not running
        self.machine.events.post('start_timer_down')
        self.advance_time_and_run(10)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        # mode should not start automatically
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes.mode_with_timers.active)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        self.machine.events.post('stop_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertFalse(self.machine.modes.mode_with_timers.active)

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes.mode_with_timers.active)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        timer = self.machine.modes.mode_with_timers.timers['timer_down']
        self.assertFalse(timer.running)

        # timer should start now
        self.machine.events.post('start_timer_down')
        self.advance_time_and_run(1)
        self.assertTrue(timer.running)

        self.assertTrue(self.started)
        self.assertEqual(0, self.tick)
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(.6)
        self.assertTrue(self.started)
        self.assertEqual(1, self.tick)
        self.assertEqual(4, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event("add_timer_down")
        self.assertEqual(6, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event("subtract_timer_down")
        self.assertEqual(4, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1.5)
        self.assertEqual(2, self.tick)
        self.assertEqual(3, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event("pause_timer_down")
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(3, self.tick)
        self.assertEqual(2, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1.5)
        self.assertEqual(4, self.tick)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1.5)
        self.assertEqual(4, self.tick)
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1.5)
        self.assertEqual(4, self.tick)
        # and complete at some point
        self.assertFalse(self.started)

        # stay off
        self.advance_time_and_run(20)
        self.assertEqual(4, self.tick)
        self.assertFalse(self.started)

        # cannot be start without reset
        self.post_event("start_timer_down")
        self.advance_time_and_run()
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.assertFalse(timer.running)

        self.post_event("reset_timer_down")
        self.advance_time_and_run()
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.assertFalse(timer.running)

        self.post_event("start_timer_down")
        self.advance_time_and_run()
        self.assertTrue(timer.running)
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run()
        self.assertEqual(4, self.machine.modes.mode_with_timers.player[timer.tick_var])

    def test_start_running(self):
        # add a fake player
        player = {}
        self.machine.mode_controller._player_turn_start(player)
        self.mock_event("timer_timer_start_running_complete")

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.machine_run()
        timer = self.machine.modes.mode_with_timers.timers['timer_start_running']
        self.assertTrue(timer.running)
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.assertEqual(0, self._events['timer_timer_start_running_complete'])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events['timer_timer_start_running_complete'])
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertTrue(timer.running)
        self.advance_time_and_run(1)
        self.assertFalse(timer.running)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._events['timer_timer_start_running_complete'])

    def test_restart_on_complete(self):
        # add a fake player
        player = {}
        self.machine.mode_controller._player_turn_start(player)

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.machine_run()
        timer = self.machine.modes.mode_with_timers.timers['timer_restart_on_complete']
        self.assertTrue(timer.running)
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])

        self.assertTrue(timer.running)

    def test_mode_timer_events(self):
        # add a fake player
        player = {}
        self.machine.mode_controller._player_turn_start(player)

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes.mode_with_timers.active)

        timer = self.machine.modes.mode_with_timers.timers['timer_up']
        self.assertFalse(timer.running)

        # timer should start now
        self.post_event('start_timer_up')
        self.assertTrue(timer.running)

        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event('reset_timer_up')

        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event('stop_timer_up')
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event('restart_timer_up')
        self.assertEqual(0, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event('jump_timer_up')
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event("change_tick_interval_timer_up")
        # 1s * 4 = 4s
        self.advance_time_and_run(1)
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(6, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(4)
        self.assertEqual(7, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event("change_tick_interval_timer_up")
        # 4s * 4 = 16s
        self.advance_time_and_run(8)
        self.assertEqual(7, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(8)
        self.assertEqual(8, self.machine.modes.mode_with_timers.player[timer.tick_var])

        self.post_event("set_tick_interval_timer_up")
        # back to 2s
        self.advance_time_and_run(1)
        self.assertEqual(8, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(1)
        self.assertEqual(9, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.advance_time_and_run(2)
        self.assertEqual(10, self.machine.modes.mode_with_timers.player[timer.tick_var])
        # and complete at some point
        self.assertFalse(timer.running)

        self.post_event('jump_timer_up')
        self.assertEqual(5, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event('jump_over_max_timer_up')
        self.assertEqual(15, self.machine.modes.mode_with_timers.player[timer.tick_var])
        self.post_event('add_timer_up')
        self.assertEqual(15, self.machine.modes.mode_with_timers.player[timer.tick_var])

    def test_interrupt_timer_by_mode_stop_with_player(self):
        self.machine.events.add_handler("timer_timer_down_tick", self._mode_timer_tick)
        self.machine.events.add_handler("timer_timer_down_started", self._mode_timer_start)
        self.machine.events.add_handler("timer_timer_down_complete", self._mode_timer_complete)
        self.machine.events.add_handler("timer_timer_down_stopped", self._mode_timer_complete)

        # add a fake player
        player = {}
        self.machine.mode_controller._player_turn_start(player)

        self.assertFalse(self.machine.modes.mode_with_timers.active)

        self.tick = 0
        self.started = False

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes.mode_with_timers.active)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        # timer should start now
        self.machine.events.post('start_timer_down')
        self.advance_time_and_run(1)

        self.assertTrue(self.started)
        self.assertEqual(0, self.tick)
        self.advance_time_and_run(.6)
        self.assertTrue(self.started)
        self.assertEqual(1, self.tick)
        self.advance_time_and_run(1.5)
        self.assertEqual(2, self.tick)

        # stop mode. timer should stop
        self.machine.events.post('stop_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertFalse(self.machine.modes.mode_with_timers.active)
        self.assertFalse(self.started)

        # and stay off
        self.advance_time_and_run(20)
        self.assertEqual(2, self.tick)
        self.assertFalse(self.started)
