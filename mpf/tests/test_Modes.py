from unittest.mock import MagicMock

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestModes(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'test_modes.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mode_tests/'

    def test_loading_modes(self):
        # Tests multi-case mode listing in config and checking here

        # assert that modes did load
        self.assertIn('mode1', self.machine.modes)
        self.assertIn('mode2', self.machine.modes)
        self.assertIn('mode3', self.machine.modes)
        self.assertIn('mode4', self.machine.modes)

    def test_mode_start_stop(self):
        # Setup mocked event handlers for mode start/stop sequence
        self.mode1_will_start_event_handler = MagicMock()
        self.mode1_starting_event_handler = MagicMock()
        self.mode1_started_event_handler = MagicMock()
        self.mode1_will_stop_event_handler = MagicMock()
        self.mode1_stopping_event_handler = MagicMock()
        self.mode1_stopped_event_handler = MagicMock()

        self.machine.events.add_handler('mode_mode1_will_start', self.mode1_will_start_event_handler)
        self.machine.events.add_handler('mode_mode1_starting', self.mode1_starting_event_handler)
        self.machine.events.add_handler('mode_mode1_started', self.mode1_started_event_handler)
        self.machine.events.add_handler('mode_mode1_will_stop', self.mode1_will_stop_event_handler)
        self.machine.events.add_handler('mode_mode1_stopping', self.mode1_stopping_event_handler)
        self.machine.events.add_handler('mode_mode1_stopped', self.mode1_stopped_event_handler)

        # start mode 1. It should only start once
        self.machine.events.post('start_mode1')
        self.machine.events.post('start_mode1')
        self.advance_time_and_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertIn(self.machine.modes.mode1,
                      self.machine.mode_controller.active_modes)
        self.assertFalse(self.machine.mode_controller.is_active('mode2'))
        self.assertFalse(self.machine.modes.mode2.active)
        self.assertIn(self.machine.modes.mode1,
                      self.machine.mode_controller.active_modes)

        # test config via include
        self.assertEqual(123, self.machine.modes.mode1.config['mode_settings']['test'])

        # start a mode that's already started and make sure it doesn't explode
        self.machine.modes.mode1.start()

        # make sure event handler were called for mode start process
        self.assertEqual(1, self.mode1_will_start_event_handler.call_count)
        self.assertEqual(1, self.mode1_starting_event_handler.call_count)
        self.assertEqual(1, self.mode1_started_event_handler.call_count)

        # stop mode 1
        self.machine.events.post('stop_mode1')
        self.advance_time_and_run()
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.assertFalse(self.machine.modes.mode1.active)

        # make sure event handler were called for mode stop process
        self.assertEqual(1, self.mode1_will_stop_event_handler.call_count)
        self.assertEqual(1, self.mode1_stopping_event_handler.call_count)
        self.assertEqual(1, self.mode1_stopped_event_handler.call_count)

    def test_custom_mode_code(self):
        self.assertTrue(self.machine.modes.mode3.custom_code)

    def test_mode_priorities(self):

        # test the start priorities TODO there's got to be a better way?
        found_it = False

        for handler in self.machine.events.registered_handlers['start_mode1']:

            if handler.callback == self.machine.modes.mode1.start:
                found_it = True
                self.assertEqual(handler.priority, 201)

        self.assertTrue(found_it)

        # default priorities
        self.machine.modes.mode1.start()
        self.advance_time_and_run()
        self.assertEqual(self.machine.modes.mode1.priority, 200)
        self.assertEqual(self.machine.modes.attract.priority, 10)
        self.assertEqual(self.machine.modes.mode1.config['mode_settings']['this'], True)

        # test the stop priorities
        found_it = False
        for handler in self.machine.events.registered_handlers['stop_mode1']:
            if handler.callback == self.machine.modes.mode1.stop:
                found_it = True
                # 201 because stop priorities are always +1 over mode priority
                self.assertEqual(handler.priority, 201)
        self.assertTrue(found_it)

        # pass a priority at start
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()
        self.machine.modes.mode1.start(mode_priority=500)
        self.advance_time_and_run()
        self.assertEqual(self.machine.modes.mode1.priority, 500)
        self.advance_time_and_run()

        # test the order of the active modes list
        self.assertEqual(self.machine.modes.mode1,
                         self.machine.mode_controller.active_modes[0])
        self.assertEqual(self.machine.modes.attract,
                         self.machine.mode_controller.active_modes[1])

    def test_mode_start_with_callback(self):
        self.mode_start_callback = MagicMock()

        self.machine.modes.mode1.start(callback=self.mode_start_callback)
        self.advance_time_and_run()
        self.mode_start_callback.assert_called_once_with()

    def test_use_wait_queue(self):
        self.callback = MagicMock()
        self.machine.events.post_queue('start_mode4',
                                       callback=self.callback)
        self.advance_time_and_run()

        # make sure the mode started
        self.assertTrue(self.machine.modes.mode4.active)
        self.advance_time_and_run()

        # callback should not be called since mode is set to use wait queue
        self.callback.assert_not_called()

        self.machine.modes.mode4.stop()
        self.advance_time_and_run()

        # once mode stops, verify that callback was called
        self.callback.assert_called_once_with()

    def test_ball_end(self):
        # mode1 is set to keep running on ball end
        # mode2 should stop and restart on ball end
        # mode3 should stop and stay stopped
        self.assertFalse(self.machine.modes.mode1.config['mode']['stop_on_ball_end'])
        self.assertTrue(self.machine.modes.mode2.config['mode']['stop_on_ball_end'])
        self.assertTrue(self.machine.modes.mode3.config['mode']['stop_on_ball_end'])

        # start a game
        self.machine.playfield.add_ball = MagicMock()
        self.machine.events.post('game_start')
        self.advance_time_and_run()
        self.machine.game.balls_in_play = 1
        self.assertTrue(self.machine.game)

        # start some modes
        self.machine.modes.mode1.start()
        self.machine.modes.mode2.start()
        self.machine.modes.mode3.start()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertTrue(self.machine.modes.mode3.active)

        # change the config of modes 1 and 2 so we can verify whether they
        # actually stopped and restarted since the configs are used to start
        # the modes
        self.machine.modes.mode1.config['mode']['priority'] = 999
        self.machine.modes.mode2.config['mode']['priority'] = 999

        # end the ball
        self.machine.game.end_ball()
        self.advance_time_and_run()

        self.assertTrue(self.machine.modes.mode1.active)
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertFalse(self.machine.modes.mode3.active)

        # since mode1 should have stayed running, its config should not change
        self.assertNotEqual(self.machine.modes.mode1.priority, 999)
        # mode2 should use the new priority since it should have restarted
        self.assertEqual(self.machine.modes.mode2.priority, 999)

        # end ball 2
        self.machine.game.end_ball()
        self.advance_time_and_run()

        # end ball 3 and end the game
        self.machine.game.end_ball()
        self.advance_time_and_run()

        self.assertTrue(self.machine.modes.attract.active)
        self.assertFalse(self.machine.modes.game.active)
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertFalse(self.machine.modes.mode2.active)
        self.assertFalse(self.machine.modes.mode3.active)


class TestModesInGame(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'test_modes_in_game.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mode_tests/'

    def test_restart_on_next_ball(self):
        """Test restart_on_next_ball."""
        self.mock_event("mode_mode_restart_on_next_ball_will_start")
        self.assertModeNotRunning("mode_restart_on_next_ball")
        self.start_game()

        self.assertModeNotRunning("mode_restart_on_next_ball")
        self.drain_ball()

        # mode shoud not be started
        self.assertModeNotRunning("mode_restart_on_next_ball")

        # start it
        self.post_event("start_mode_restart_on_next_ball")
        self.advance_time_and_run()

        # it should run
        self.assertModeRunning("mode_restart_on_next_ball")
        self.assertEventCalled("mode_mode_restart_on_next_ball_will_start", 1)

        # check that mode is restarted on next ball
        self.mock_event("mode_mode_restart_on_next_ball_will_start")
        self.drain_ball()
        self.assertModeRunning("mode_restart_on_next_ball")
        self.assertEventCalled("mode_mode_restart_on_next_ball_will_start", 1)
