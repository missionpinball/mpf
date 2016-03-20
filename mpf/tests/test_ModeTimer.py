# TODO: test remaining actions
# TODO: test empty control_events

from mpf.tests.MpfTestCase import MpfTestCase


class TestModeTimer(MpfTestCase):

    def getConfigFile(self):
        return 'test_mode_timers.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mode_tests/'

    def _mode_timer_start(self, **kwargs):
        self.started = True

    def _mode_timer_tick(self, **kwargs):
        self.tick += 1

    def _mode_timer_complete(self, **kwargs):
        self.started = False

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
        self.advance_time_and_run(1.5)
        self.assertEqual(3, self.tick)
        self.advance_time_and_run(1.5)
        self.assertEqual(4, self.tick)
        self.advance_time_and_run(1.5)
        self.assertEqual(4, self.tick)
        # and complete at some point
        self.assertFalse(self.started)

        # stay off
        self.advance_time_and_run(20)
        self.assertEqual(4, self.tick)
        self.assertFalse(self.started)


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
