from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestModes(MpfTestCase):

    def getConfigFile(self):
        return 'test_modes.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mode_tests/'

    def test_loading_modes(self):
        # Tests multi-case mode listing in config and checking here

        # lowercase in config, lowercase folder
        self.assertIn('mode1', self.machine.modes)
        # uppercase in config, lowercase folder
        self.assertIn('mode2', self.machine.modes)
        # lowercase config, uppercase folder
        self.assertIn('mode3', self.machine.modes)
        # lowercase config, lowercase folder, uppercase here
        self.assertIn('Mode4', self.machine.modes)

    def test_mode_start_stop(self):
        # start mode 1
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

        # stop mode 1
        self.machine.events.post('stop_mode1')
        self.advance_time_and_run()
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.assertFalse(self.machine.modes.mode1.active)

    def test_custom_mode_code(self):
        self.assertTrue(self.machine.modes.mode3.custom_code)

    def test_mode_priorities(self):

        # test the start priorities TODO there's got to be a better way?
        found_it = False

        for callback, priority, _, _ \
                in self.machine.events.registered_handlers['start_mode1']:

            if callback == self.machine.modes.mode1.start:
                found_it = True
                self.assertEqual(priority, 201)

        self.assertTrue(found_it)

        # default priorities
        self.machine.modes.mode1.start()
        self.machine.modes.mode2.start()
        self.advance_time_and_run()
        self.assertEqual(self.machine.modes.mode1.priority, 200)
        self.assertEqual(self.machine.modes.mode2.priority, 100)
        self.assertEqual(self.machine.modes.attract.priority, 10)

        # test the stop priorities
        found_it = False
        for callback, priority, _, _ \
                in self.machine.events.registered_handlers['stop_mode1']:
            if callback == self.machine.modes.mode1.stop:
                found_it = True
                # 201 because stop priorities are always +1 over mode priority
                self.assertEqual(priority, 201)
        self.assertTrue(found_it)

        found_it = False
        for callback, priority, _, _ \
                in self.machine.events.registered_handlers['stop_mode2']:
            if callback == self.machine.modes.mode2.stop:
                found_it = True
                # base priority 100, +1 default bump, +2 stop_priority config
                self.assertEqual(priority, 103)
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
        self.assertEqual(self.machine.modes.mode2,
                         self.machine.mode_controller.active_modes[1])
        self.assertEqual(self.machine.modes.attract,
                         self.machine.mode_controller.active_modes[2])

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
        self.machine.game.ball_ending()
        self.advance_time_and_run()

        self.assertTrue(self.machine.modes.mode1.active)
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertFalse(self.machine.modes.mode3.active)

        # since mode1 should have stayed running, its config should not change
        self.assertNotEqual(self.machine.modes.mode1.priority, 999)
        # mode2 should use the new priority since it should have restarted
        self.assertEqual(self.machine.modes.mode2.priority, 999)

        # end ball 2
        self.machine.game.ball_ending()
        self.advance_time_and_run()

        # end ball 3 and end the game
        self.machine.game.ball_ending()
        self.advance_time_and_run()

        self.assertTrue(self.machine.modes.attract.active)
        self.assertFalse(self.machine.modes.game.active)
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertFalse(self.machine.modes.mode2.active)
        self.assertFalse(self.machine.modes.mode3.active)
