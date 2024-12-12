# TODO: test remaining actions
# TODO: test empty control_events

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestTimer(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'test_timer.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/timer/'

    def _timer_start(self, **kwargs):
        del kwargs
        self.started = True

    def _timer_tick(self, **kwargs):
        del kwargs
        self.tick += 1

    def _timer_complete(self, **kwargs):
        del kwargs
        self.started = False

    def test_start_with_game(self):
        self.start_game()
        self.advance_time_and_run()
        self.assertIn(self.machine.modes["mode_with_timers2"],
                      self.machine.mode_controller.active_modes)

        self.assertIn(self.machine.modes["game"],
                      self.machine.mode_controller.active_modes)

    def test_timer_down_outside_of_game(self):
        self.machine.events.add_handler("timer_timer_down_tick", self._timer_tick)
        self.machine.events.add_handler("timer_timer_down_started", self._timer_start)
        self.machine.events.add_handler("timer_timer_down_complete", self._timer_complete)
        self.machine.events.add_handler("timer_timer_down_stopped", self._timer_complete)

        self.assertFalse(self.machine.modes["mode_with_timers"].active)

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
        self.assertTrue(self.machine.modes["mode_with_timers"].active)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        self.machine.events.post('stop_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertFalse(self.machine.modes["mode_with_timers"].active)

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes["mode_with_timers"].active)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        timer = self.machine.timers['timer_down']
        self.assertFalse(timer.running)

        # timer should start now
        self.machine.events.post('start_timer_down')
        self.advance_time_and_run(1)
        self.assertTrue(timer.running)

        self.assertTrue(self.started)
        self.assertEqual(1, self.tick)
        self.assertEqual(5, timer.ticks)
        self.advance_time_and_run(.6)
        self.assertTrue(self.started)
        self.assertEqual(2, self.tick)
        self.assertEqual(4, timer.ticks)
        self.post_event("add_timer_down")
        self.assertEqual(6, timer.ticks)
        self.post_event("subtract_timer_down")
        self.assertEqual(4, timer.ticks)
        self.advance_time_and_run(1.5)
        self.assertEqual(3, self.tick)
        self.assertEqual(3, timer.ticks)
        self.post_event("pause_timer_down")
        self.advance_time_and_run(0.5)
        self.assertEqual(3, self.tick)
        self.assertEqual(3, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.tick)
        self.assertEqual(3, timer.ticks)
        self.advance_time_and_run(1)
        # Resuming the paused timer re-ticks at the last number,
        # so self.ticks increases but timer.ticks does not
        self.assertEqual(4, self.tick)
        self.assertEqual(3, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(5, self.tick)
        self.assertEqual(2, timer.ticks)
        self.advance_time_and_run(1.5)
        self.assertEqual(6, self.tick)
        self.assertEqual(1, timer.ticks)
        self.advance_time_and_run(1.5)
        self.assertEqual(6, self.tick)
        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1.5)
        self.assertEqual(6, self.tick)
        # and complete at some point
        self.assertFalse(self.started)

        # stay off
        self.advance_time_and_run(20)
        self.assertEqual(6, self.tick)
        self.assertFalse(self.started)

        # cannot be start without reset
        self.post_event("start_timer_down")
        self.advance_time_and_run()
        self.assertEqual(0, timer.ticks)
        self.assertFalse(timer.running)

        self.post_event("reset_timer_down")
        self.advance_time_and_run()
        self.assertEqual(5, timer.ticks)
        self.assertFalse(timer.running)

        self.post_event("start_timer_down")
        self.advance_time_and_run()
        self.assertTrue(timer.running)
        self.assertEqual(5, timer.ticks)
        self.advance_time_and_run()
        self.assertEqual(4, timer.ticks)

    def test_change_tick(self):
        self.start_mode("mode_with_timers")
        self.mock_event("timer_timer_change_tick_tick")
        self.advance_time_and_run()
        self.post_event("timer_change_tick_start")
        self.advance_time_and_run(.1)
        self.assertEventCalled("timer_timer_change_tick_tick", 1)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 2)
        self.post_event("timer_change_tick_event")
        self.assertEventCalled("timer_timer_change_tick_tick", 2)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 12)

    def test_set_tick_fixed(self):
        self.start_mode("mode_with_timers")
        self.mock_event("timer_timer_change_tick_tick")
        self.advance_time_and_run()
        self.post_event("timer_change_tick_start")
        self.advance_time_and_run(.1)
        self.assertEventCalled("timer_timer_change_tick_tick", 1)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 2)
        self.post_event("timer_set_tick_event_fixed")
        self.assertEventCalled("timer_timer_change_tick_tick", 2)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 7)

    def test_set_tick_kwarg(self):
        self.start_mode("mode_with_timers")
        self.mock_event("timer_timer_change_tick_tick")
        self.advance_time_and_run()
        self.post_event("timer_change_tick_start")
        self.advance_time_and_run(.1)
        self.assertEventCalled("timer_timer_change_tick_tick", 1)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 2)
        self.post_event_with_params("timer_set_tick_event_kwarg", event_value=0.1)
        self.assertEventCalled("timer_timer_change_tick_tick", 2)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 12)
        self.post_event_with_params("timer_set_tick_event_kwarg", event_value=0.2)
        self.assertEventCalled("timer_timer_change_tick_tick", 12)
        self.advance_time_and_run(1)
        self.assertEventCalled("timer_timer_change_tick_tick", 17)

    def test_start_running(self):
        # add a fake player
        self.start_game()
        self.mock_event("timer_timer_start_running_complete")

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.machine_run()
        timer = self.machine.timers['timer_start_running']
        self.assertTrue(timer.running)
        self.assertEqual(0, timer.ticks)
        self.assertEqual(0, self._events['timer_timer_start_running_complete'])
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
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
        self.start_game()

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.machine_run()
        timer = self.machine.timers['timer_restart_on_complete']
        self.assertTrue(timer.running)
        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(2, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(3, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(4, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(2, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(3, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(4, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(0, timer.ticks)

        self.assertTrue(timer.running)

    def test_timer_events(self):
        # add a fake player
        self.start_game()

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes["mode_with_timers"].active)

        timer = self.machine.timers['timer_up']
        self.assertFalse(timer.running)

        # timer should start now
        self.post_event('start_timer_up')
        self.assertTrue(timer.running)

        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(2, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(3, timer.ticks)
        self.post_event('reset_timer_up')

        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
        self.post_event('stop_timer_up')
        self.assertEqual(1, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
        self.post_event('restart_timer_up')
        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)
        self.post_event('jump_timer_up')
        self.assertEqual(5, timer.ticks)
        self.post_event_with_params("change_tick_interval_timer_up", change=1)
        # 1s * 4 = 4s
        self.advance_time_and_run(1)
        self.assertEqual(5, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(5, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(5, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(6, timer.ticks)
        self.advance_time_and_run(4)
        self.assertEqual(7, timer.ticks)
        self.post_event("change_tick_interval_timer_up")
        # 4s * 4 = 16s
        self.advance_time_and_run(8)
        self.assertEqual(7, timer.ticks)
        self.advance_time_and_run(8)
        self.assertEqual(8, timer.ticks)

        self.post_event("set_tick_interval_timer_up")
        # back to 2s
        self.advance_time_and_run(1)
        self.assertEqual(8, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(9, timer.ticks)
        self.advance_time_and_run(2)
        self.assertEqual(10, timer.ticks)
        # and complete at some point
        self.assertFalse(timer.running)

        self.post_event('jump_timer_up')
        self.assertEqual(5, timer.ticks)
        self.post_event('jump_over_max_timer_up')
        self.assertEqual(15, timer.ticks)
        self.post_event('add_timer_up')
        self.assertEqual(15, timer.ticks)

        self.post_event('restart_timer_up')
        self.post_event("reset_tick_interval")
        self.advance_time_and_run()
        self.assertEqual(1, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(2, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(3, timer.ticks)
        self.post_event("change_tick_interval_timer_up")
        self.advance_time_and_run(4)
        self.assertEqual(4, timer.ticks)
        self.post_event("reset_tick_interval")
        self.advance_time_and_run()
        self.assertEqual(5, timer.ticks)

        # Ensure that we get the 0 tick when it restarts
        self.mock_event("timer_timer_up_tick")
        self.post_event('restart_timer_up')
        self.assertEqual(0, timer.ticks)
        self.assertEventCalledWith("timer_timer_up_tick",
                                   ticks=0, ticks_remaining=10)

    def test_interrupt_timer_by_mode_stop_with_player(self):
        self.machine.events.add_handler("timer_timer_down_tick", self._timer_tick)
        self.machine.events.add_handler("timer_timer_down_started", self._timer_start)
        self.machine.events.add_handler("timer_timer_down_complete", self._timer_complete)
        self.machine.events.add_handler("timer_timer_down_stopped", self._timer_complete)

        # add a fake player
        self.start_game()

        self.assertFalse(self.machine.modes["mode_with_timers"].active)

        self.tick = 0
        self.started = False

        # start mode
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes["mode_with_timers"].active)
        self.assertFalse(self.started)
        self.assertEqual(0, self.tick)

        # timer should start now
        self.machine.events.post('start_timer_down')
        self.advance_time_and_run(1)

        self.assertTrue(self.started)
        self.assertEqual(1, self.tick)
        self.advance_time_and_run(.6)
        self.assertTrue(self.started)
        self.assertEqual(2, self.tick)
        self.advance_time_and_run(1.5)
        self.assertEqual(3, self.tick)

        # stop mode. timer should stop
        self.machine.events.post('stop_mode_with_timers')
        self.advance_time_and_run(10)
        self.assertFalse(self.machine.modes["mode_with_timers"].active)
        self.assertFalse(self.started)

        # and stay off
        self.advance_time_and_run(20)
        self.assertEqual(3, self.tick)
        self.assertFalse(self.started)

    def test_mode_timer_with_player_var(self):
        # add a fake player
        self.start_game()

        # start mode. no player vars
        self.mock_event("timer_timer_player_var_complete")
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(.1)

        self.assertEventCalled("timer_timer_player_var_complete")
        self.machine.events.post('stop_mode_with_timers')
        self.advance_time_and_run(.1)

        # set player vars. timer should run 5s
        self.machine.game.player.start = 2
        self.machine.game.player.end = 7

        self.machine.log.debug("START")
        self.mock_event("timer_timer_player_var_complete")
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(4.5)
        self.machine.log.debug("END")
        self.assertEventNotCalled("timer_timer_player_var_complete")

        self.advance_time_and_run(0.6)

        self.assertEventCalled("timer_timer_player_var_complete")
        self.machine.events.post('stop_mode_with_timers')

    def test_timer_control_with_player_var(self):
        self.start_game()
        self.machine.game.player.timer_amount = 10
        timer = self.machine.timers['timer_with_player_var_control_events']

        self.machine.events.post('start_player_var_timer')
        self.advance_time_and_run(.1)
        self.assertTrue(timer.running)
        self.assertEqual(0, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(1, timer.ticks)

        self.machine.events.post('add_player_var_timer')
        self.advance_time_and_run(.1)
        self.assertEqual(11, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(12, timer.ticks)

        self.machine.game.player.timer_amount = 5
        self.machine.events.post('subtract_player_var_timer')
        self.advance_time_and_run(.1)
        self.assertEqual(7, timer.ticks)
        self.advance_time_and_run(1)
        self.assertEqual(8, timer.ticks)

    def test_timer_player_vars_with_multiplayer(self):
        # add a fake player
        self.start_two_player_game()

        self.assertPlayerNumber(1)
        self.assertBallNumber(1)
        self.advance_time_and_run(.1)

        timer = self.machine.timers['timer_start_with_game']
        # In this test scenario, the timer is at 2 ticks by the time we get here
        self.assertEqual(2, timer.ticks)

        self.advance_time_and_run(1)
        self.assertEqual(self.machine.game.player_list[0].mode_with_timers2_timer_start_with_game_tick, 3)
        self.advance_time_and_run(1)
        self.assertEqual(self.machine.game.player_list[0].mode_with_timers2_timer_start_with_game_tick, 4)

        self.machine.events.post('stop_mode_with_timers2')
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertPlayerNumber(2)
        self.assertBallNumber(1)
        self.machine.events.post('start_mode_with_timers')
        self.advance_time_and_run(.1)

        self.assertEqual(self.machine.game.player_list[0].mode_with_timers2_timer_start_with_game_tick, 4)
        self.assertEqual(self.machine.game.player_list[1].mode_with_timers2_timer_start_with_game_tick, 2)
        self.advance_time_and_run(1)
        self.assertEqual(self.machine.game.player_list[0].mode_with_timers2_timer_start_with_game_tick, 4)
        self.assertEqual(self.machine.game.player_list[1].mode_with_timers2_timer_start_with_game_tick, 3)
        self.advance_time_and_run(1)
        self.assertEqual(self.machine.game.player_list[0].mode_with_timers2_timer_start_with_game_tick, 4)
        self.assertEqual(self.machine.game.player_list[1].mode_with_timers2_timer_start_with_game_tick, 4)
        self.advance_time_and_run(1)
        self.assertEqual(self.machine.game.player_list[0].mode_with_timers2_timer_start_with_game_tick, 4)
        self.assertEqual(self.machine.game.player_list[1].mode_with_timers2_timer_start_with_game_tick, 5)
