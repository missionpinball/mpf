from unittest.mock import MagicMock

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestShots(MpfTestCase):

    def getConfigFile(self):
        return 'test_shots.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/shots/'

    def setUp(self):
        super(TestShots, self).setUp()
        self.min_frame_time = 0.5

    def start_game(self):
        # shots only work in games so we have to do this a lot
        self.machine.playfield.add_ball = MagicMock()
        self.machine.events.post('game_start')
        self.advance_time_and_run(1.02)
        self.machine.game.balls_in_play = 1
        self.assertIsNotNone(self.machine.game)

    def stop_game(self):
        # stop game
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def test_loading_shots(self):
        # Make sure machine-wide shots load & mode-specific shots do not
        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

        self.assertFalse(self.machine.shots.mode1_shot_1.enabled)

        # Start the mode and make sure those shots load
        self.machine.modes.mode1.start()
        self.advance_time_and_run()
        self.assertTrue(self.machine.shots.mode1_shot_1.enabled)

        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

        # Stop the mode and make sure those shots go away
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()
        self.assertFalse(self.machine.shots.mode1_shot_1.enabled)

        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

    def test_hits(self):
        self.shot_1_hit = MagicMock()
        self.shot_1_default_hit = MagicMock()
        self.shot_1_default_unlit_hit = MagicMock()
        self.mode1_shot_1_hit = MagicMock()
        self.machine.events.add_handler('shot_1_hit', self.shot_1_hit)
        self.machine.events.add_handler('shot_1_default_hit',
                                        self.shot_1_default_hit)
        self.machine.events.add_handler('shot_1_default_unlit_hit',
                                        self.shot_1_default_unlit_hit)
        self.machine.events.add_handler('mode1_shot_1_hit',
                                        self.mode1_shot_1_hit)

        # make sure shot does not work with no game in progress
        self.hit_and_release_switch('switch_1')
        self.advance_time_and_run()
        self.shot_1_hit.assert_not_called()

        self.start_game()

        # hit shot_1, test all three event variations
        self.hit_and_release_switch('switch_1')
        self.advance_time_and_run()

        self.shot_1_hit.assert_called_once_with(profile='default',
                                                state='unlit')
        self.shot_1_default_hit.assert_called_once_with(profile='default',
                                                        state='unlit')
        self.shot_1_default_unlit_hit.assert_called_once_with(
            profile='default', state='unlit')

        # hit the mode shot and make sure it doesn't fire
        self.hit_and_release_switch('switch_3')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

        # Start the mode
        self.machine.modes.mode1.start()
        self.advance_time_and_run()

        # hit the mode shot and make sure it was called
        self.hit_and_release_switch('switch_3')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_called_once_with(profile='default',
                                                      state='unlit')

        # stop the mode
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()

        # hit the mode shot and make sure it was not called
        self.mode1_shot_1_hit = MagicMock()
        self.hit_and_release_switch('switch_3')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

        # stop the game (should not crash)
        self.stop_game()

        # hit the shot and make sure it was not called again
        self.hit_and_release_switch('switch_1')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

    def test_shot_with_multiple_switches(self):
        self.shot_15_hit = MagicMock()
        self.machine.events.add_handler('shot_15_hit', self.shot_15_hit)
        self.start_game()

        # hit shot_15 via switch_13
        self.hit_and_release_switch('switch_13')
        self.shot_15_hit.assert_called_once_with(profile='default',
                                                 state='unlit')

        # hit shot_15 via switch_14
        self.shot_15_hit.reset_mock()
        self.hit_and_release_switch('switch_14')
        self.shot_15_hit.assert_called_once_with(profile='default',
                                                 state='lit')

    def test_shot_sequence(self):
        self.mock_event("shot_sequence_hit")
        self.start_game()

        # test too slow hit
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(3)
        self.hit_and_release_switch("switch_2")
        self.advance_time_and_run(1)
        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events["shot_sequence_hit"])

        # test fast enough hit
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(1)
        self.hit_and_release_switch("switch_2")
        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(1)
        self.assertEqual(1, self._events["shot_sequence_hit"])

    def test_shot_sequence_delay(self):
        self.mock_event("shot_sequence_hit")
        self.start_game()

        # test delay at the beginning. should not count
        self.hit_and_release_switch("s_delay")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_2")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events["shot_sequence_hit"])

        self.advance_time_and_run(10)

        # test delay_switch after first switch. should still count
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("s_delay")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_2")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(1)
        self.assertEqual(1, self._events["shot_sequence_hit"])

    def test_shot_sequence_cancel(self):
        self.mock_event("shot_sequence_hit")
        self.start_game()

        # start the sequence
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_2")
        self.advance_time_and_run(.5)

        # hit the cancel switch
        self.hit_and_release_switch("switch_4")

        # hit the final switch in the sequence, shot should not be hit since it
        # was canceled
        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events["shot_sequence_hit"])

    def test_profile_advancing_no_loop(self):
        self.start_game()
        self.mock_event("shot_27_hit")
        # unlit and two states in the beginning
        self.assertEqual(2, len(self.machine.shots.shot_1.get_profile_by_key('mode', None)[
                                'settings']['states']))
        self.assertEqual("unlit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])

        # one hit and it lits
        self.hit_and_release_switch("switch_1")
        self.assertEqual("lit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual(1, self.machine.game.player["shot_1_default"])

        # it stays lit
        self.hit_and_release_switch("switch_1")
        self.assertEqual("lit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual(1, self.machine.game.player["shot_1_default"])
        self.assertEventCalled("shot_27_hit")

    def test_shots_with_events(self):
        self.start_game()
        self.mock_event("shot_28_hit")
        self.post_event("event2")
        self.post_event("event1")
        self.assertEventNotCalled("shot_28_hit")

        self.post_event("event2")
        self.assertEventCalled("shot_28_hit")

    def test_profile_advancing_with_loop(self):
        self.start_game()

        self.assertEqual(3, len(self.machine.shots.shot_2.get_profile_by_key('mode', None)[
                                'settings']['states']))

        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("two", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual(1,
                         self.machine.game.player["shot_2_three_states_loop"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("three", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual(2,
                         self.machine.game.player["shot_2_three_states_loop"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual(0,
                         self.machine.game.player["shot_2_three_states_loop"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("two", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual(1,
                         self.machine.game.player["shot_2_three_states_loop"])

    def test_default_show_light(self):
        self.start_game()
        self.assertEqual(0, self.machine.lights.light_1.hw_driver.current_brightness)

        self.hit_and_release_switch("switch_5")
        self.advance_time_and_run()
        self.assertEqual(255, self.machine.lights.light_1.hw_driver.current_brightness)

    def test_default_show_lights(self):
        self.start_game()
        self.assertEqual(0, self.machine.lights.light_1.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_2.hw_driver.current_brightness)

        self.hit_and_release_switch("switch_6")
        self.advance_time_and_run()
        self.assertEqual(255, self.machine.lights.light_1.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.lights.light_2.hw_driver.current_brightness)

    def test_default_show_led(self):
        self.start_game()
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led_1.hw_driver.current_color)

        self.hit_and_release_switch("switch_7")
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('white').rgb),
                         self.machine.leds.led_1.hw_driver.current_color)

    def test_default_show_leds(self):
        self.start_game()
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led_1.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led_2.hw_driver.current_color)

        self.hit_and_release_switch("switch_8")
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('white').rgb),
                         self.machine.leds.led_1.hw_driver.current_color)
        self.assertEqual(list(RGBColor('white').rgb),
                         self.machine.leds.led_2.hw_driver.current_color)

    def test_show_in_shot_profile_root(self):
        self.start_game()

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

        # make sure the show is not auto advancing
        self.advance_time_and_run(5)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

        self.advance_time_and_run(5)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

        # make sure it stays on green

        self.advance_time_and_run(5)
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_3.hw_driver.current_color)

    def test_show_in_step(self):
        self.start_game()
        # start_game() advances the time 1 sec, so by now we're already on
        # step 2 of the rainbow show

        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_11.hw_driver.current_color)

        # make sure show is advancing on its own
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_11.hw_driver.current_color)

        # hit the shot, changes to show1
        self.hit_and_release_switch("switch_11")
        self.advance_time_and_run(0.1)
        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_11.hw_driver.current_color)

        # make sure show is advancing on its own
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_11.hw_driver.current_color)

    def test_combined_show_in_profile_root_and_step(self):
        # tests a show defined in a profile root which is used for most steps,
        # but a separate show in certain steps that is used just for that step

        self.start_game()
        self.advance_time_and_run()

        # we're on step 1
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # step 2
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # since this is a root show, it should not be advancing on its own, so
        # advance the time a few times and make sure the led doesn't change
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # step 3 is rainbow 2 show, so make sure it switches
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run(0.02)
        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # since this is a show in a step, it should be auto advancing, so keep
        # checking every sec to make sure the colors are changing
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('aquamarine').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('azure').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # it should loop
        self.advance_time_and_run(1)

        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # hit the switch, should advance to step 4, which is back to the
        # rainbow show
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # show should not be advancing without a hit
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

        # hit to verify advance
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led_12.hw_driver.current_color)

    def test_step_with_no_show_after_step_with_show(self):
        self.start_game()

        # start_game() advances the time 1 sec, so by now we're already on
        # step 2 of the rainbow show

        # profile step 1, show1 is running
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_13.hw_driver.current_color)

        # step 2 has no show, so rainbow should still be running
        self.hit_and_release_switch("switch_13")
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_13.hw_driver.current_color)

        # make sure it's still advancing even with no switch hits
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_13.hw_driver.current_color)

        # hit the shot again, we switch to show 2
        self.hit_and_release_switch("switch_13")
        self.advance_time_and_run(0.1)
        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_13.hw_driver.current_color)

        # make sure that show is running with no more hits
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_13.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('aquamarine').rgb),
                         self.machine.leds.led_13.hw_driver.current_color)

    def test_show_ending_no_loop(self):
        # tests that if a show is set to loops: 0, that it truly stops on the
        # last step. Note that loops here is really a setting of the show
        # player, so if this works, that means that all of the show player
        # settings will work in a show tied to a shot.

        self.start_game()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_14.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_14.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_14.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led_14.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('purple').rgb),
                         self.machine.leds.led_14.hw_driver.current_color)

        # show is done, but hold is true by default in shows started from shots
        # so make sure the led stays in its final state
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('purple').rgb),
                         self.machine.leds.led_14.hw_driver.current_color)

    def test_control_events(self):
        # test control events from machine-wide shot
        shot16 = self.machine.shots.shot_16
        self.mock_event("shot_16_hit")
        self.start_game()

        # Since this shot has custom enable events, it should not be enabled on
        # game start
        self.assertFalse(shot16.enabled)

        # Also verify hit event does not register a hit
        self.machine.events.post('custom_hit_16')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["shot_16_hit"])

        # test enabling via event
        self.machine.events.post('custom_enable_16')
        self.advance_time_and_run()
        self.assertTrue(shot16.enabled)

        # test hit event
        self.machine.events.post('custom_hit_16')
        self.advance_time_and_run()
        self.assertEqual(1, self._events["shot_16_hit"])
        self.assertEqual(shot16.profiles[0]['current_state_name'], 'lit')

        # test reset event
        self.machine.events.post('custom_reset_16')
        self.advance_time_and_run()
        self.assertEqual(shot16.profiles[0]['current_state_name'], 'unlit')

        # test advance event
        self.machine.events.post('custom_advance_16')
        self.advance_time_and_run()
        # hit should not be posted again (still 1 from before)
        self.assertEqual(1, self._events["shot_16_hit"])
        # profile should have advanced though
        self.assertEqual(shot16.profiles[0]['current_state_name'], 'lit')

        # test disable event
        self.machine.events.post('custom_disable_16')
        self.advance_time_and_run()
        self.assertFalse(shot16.enabled)

        # hit the shot to make sure it's really disabled
        self.machine.events.post('custom_hit_16')
        self.advance_time_and_run()
        self.assertEqual(1, self._events["shot_16_hit"])  # still 1 from before
        self.assertEqual(shot16.profiles[0]['current_state_name'], 'lit')

        # mode1 is not active, so make sure none of the events from
        # mode1_shot_17

        self.assertFalse(self.machine.shots.mode1_shot_17.enabled)
        self.mock_event("mode1_shot_17_hit")

        # Also verify hit event does not register a hit
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["mode1_shot_17_hit"])

        # test enabling via event, shot should not work
        self.machine.events.post('custom_enable_17')
        self.advance_time_and_run()

        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["mode1_shot_17_hit"])

        # test reset event, nothing should happen
        self.machine.events.post('custom_reset_17')
        self.advance_time_and_run()

        # test disable event, nothing should happen
        self.machine.events.post('custom_disable_17')
        self.advance_time_and_run()

        # start the mode
        self.machine.modes.mode1.start()
        self.advance_time_and_run()

        shot17 = self.machine.shots.mode1_shot_17

        # Since this shot has custom enable events, it should not be enabled on
        # game start
        self.assertFalse(shot17.enabled)

        # Also verify hit event does not register a hit
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["mode1_shot_17_hit"])

        # test enabling via event
        self.machine.events.post('custom_enable_17')
        self.advance_time_and_run()
        self.assertTrue(shot17.enabled)

        # test hit event
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(1, self._events["mode1_shot_17_hit"])
        self.assertEqual(shot17.profiles[0]['current_state_name'], 'lit')

        # test reset event
        self.machine.events.post('custom_reset_17')
        self.advance_time_and_run()
        self.assertEqual(shot17.profiles[0]['current_state_name'], 'unlit')

        # test disable event
        self.machine.events.post('custom_disable_17')
        self.advance_time_and_run()
        self.assertFalse(shot17.enabled)

        # hit the shot to make sure it's really disabled
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        # since it's disabled, there should still only be 1 from before
        self.assertEqual(1, self._events["mode1_shot_17_hit"])
        self.assertEqual(shot17.profiles[0]['current_state_name'], 'unlit')

    def test_advance(self):
        self.mock_event("shot_17_hit")
        shot17 = self.machine.shots.shot_17

        self.start_game()

        # shot profile config has advance_on_hit: false
        self.hit_and_release_switch("switch_17")
        # verify it was hit, but it didn't advance
        self.assertEqual(1, self._events["shot_17_hit"])
        self.assertEqual("one", shot17.get_profile_by_key('mode', None)[
            'current_state_name'])

        # again
        self.hit_and_release_switch("switch_17")
        self.assertEqual(2, self._events["shot_17_hit"])
        self.assertEqual("one", shot17.get_profile_by_key('mode', None)['current_state_name'])

        # manual advance
        shot17.advance(steps=2)
        self.assertEqual("three", shot17.get_profile_by_key('mode', None)['current_state_name'])

        # hit still doesn't advance
        self.hit_and_release_switch("switch_17")
        self.assertEqual(3, self._events["shot_17_hit"])
        self.assertEqual("three", shot17.get_profile_by_key('mode', None)['current_state_name'])

        # disable the shot, advance should be disabled too
        shot17.disable()
        shot17.advance()
        self.assertEqual(2, self.machine.game.player.shot_17_profile_17)

        # though we can force it to advance
        shot17.advance(force=True)
        self.assertEqual(3, self.machine.game.player.shot_17_profile_17)

    def test_custom_player_variable(self):
        self.start_game()

        self.assertEqual(self.machine.game.player.hello, 0)
        self.hit_and_release_switch('switch_18')
        self.assertEqual(self.machine.game.player.hello, 1)

    def test_show_when_disabled(self):
        # first test show_when_disabled == true

        shot19 = self.machine.shots.shot_19

        self.start_game()
        # shot19 config has enable_events: none, so it should be disabled
        self.assertFalse(shot19.enabled)

        # start_game() includes a 1 sec advance time, so by now this show is
        # already on step 2
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # make sure the show keeps running
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # enable the shot
        shot19.enable()
        self.advance_time_and_run(.1)

        self.assertTrue(
            shot19.get_profile_by_key('mode', None)['settings']['show_when_disabled'])

        # show should still be at the same step
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # but it should also still be running
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # hit the shot
        shot19.hit()
        self.advance_time_and_run(.1)

        # should switch to the second show
        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # and that show should be running
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # disable the shot
        shot19.disable()

        # color should not change
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

        # and show should still be running
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_19.hw_driver.current_color)

    def test_no_show_when_disabled(self):
        shot20 = self.machine.shots.shot_20

        self.start_game()

        # shot20 config has enable_events: none, so it should be disabled
        self.assertFalse(shot20.enabled)

        # make sure the show is not running and not affecting the LED
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led_20.hw_driver.current_color)

        # enable the shot, show should start
        shot20.enable()

        self.assertFalse(
            shot20.get_profile_by_key('mode', None)['settings']['show_when_disabled'])

        self.advance_time_and_run(.1)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_20.hw_driver.current_color)

        # make sure show is advancing
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_20.hw_driver.current_color)

        # hit the shot, show should switch
        shot20.hit()
        self.advance_time_and_run(.1)

        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_20.hw_driver.current_color)

        # and that show should be running
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_20.hw_driver.current_color)

        # disable the shot
        shot20.disable()
        self.advance_time_and_run()

        # LEDs should be off since show_when_disabled == false
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led_20.hw_driver.current_color)

    def test_block(self):
        # test shot profiles from a higher priority mode to block hits to lower
        # modes

        self.start_game()
        self.machine.modes.mode1.start()
        self.machine.shots.shot_21.hit()

        # check the states of the shots.
        # player vars for shots are <shot>_<profile>
        # shot_21, mode1_shot_21 should have advanced
        self.assertEqual(1, self.machine.game.player.shot_21_mode1_shot_21)

        # but since it was set to block, the machine base profile should not
        self.assertEqual(0, self.machine.game.player.shot_21_profile_21)

    def test_no_block(self):
        # test shot profiles from a higher priority mode when block == false

        # internally this is called "waterfalling" hits, since the hit is
        # always registered by the highest priority profile, and then if it
        # does not block, it waterfalls down to the next one, etc.

        self.start_game()
        self.machine.modes.mode1.start()

        self.machine.shots.shot_22.hit()

        # check the states of the shots.
        self.assertEqual(1, self.machine.game.player.shot_22_mode1_shot_22)

        # no blocking, so the base profile should have advanced too
        self.assertEqual(1, self.machine.game.player.shot_22_profile_22)

    def test_multi_level_blocking(self):
        # test highest mode does not block, next mode blocks

        self.start_game()
        self.machine.modes.mode1.start()
        self.machine.modes.mode2.start()

        self.machine.shots.shot_21.hit()
        # mode2 should hit, does not block
        self.assertEqual(1, self.machine.game.player.shot_21_mode2_shot_21)

        # mode1 should hit, but blocks
        self.assertEqual(1, self.machine.game.player.shot_21_mode1_shot_21)

        # base mode should not hit
        self.assertEqual(0, self.machine.game.player.shot_21_profile_21)

        self.machine.shots.shot_22.hit()
        # mode2 should hit, does not block
        self.assertEqual(1, self.machine.game.player.shot_22_mode2_shot_22)

        # mode1 should hit, does not block
        self.assertEqual(1, self.machine.game.player.shot_22_mode1_shot_22)

        # base mode should hit
        self.assertEqual(1, self.machine.game.player.shot_22_profile_22)

    def test_remove_active_profile(self):
        self.start_game()
        self.machine.modes.mode1.start()
        self.machine.modes.mode2.start()

        shot22 = self.machine.shots.shot_22

        shot22.remove_active_profile()

        # todo need to finish this

    def test_show_in_higher_profile(self):
        self.start_game()

        # make sure show is running from base config
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        # advance to make sure show is running
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        # start mode1, should flip to show 2 colors
        self.machine.modes.mode1.start()
        self.advance_time_and_run(0.02)

        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        # advance to make sure show is running
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('antiquewhite').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('aquamarine').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        # stop the mode, make sure the show from the base is still running
        self.machine.modes.mode1.stop()
        self.advance_time_and_run(0.02)
        self.assertEqual(list(RGBColor('yellow').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led_23.hw_driver.current_color)

    def test_hold_true(self):
        self.start_game()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_24.hw_driver.current_color)

        # advance the time past the end of the show and make sure that the
        # led is still on
        # all these separate entries are needed due to the way the tests run
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('purple').rgb),
                         self.machine.leds.led_24.hw_driver.current_color)

    def test_hold_false(self):
        self.start_game()
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led_25.hw_driver.current_color)

        # advance the time past the end of the show and make sure that the
        # led is off
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led_25.hw_driver.current_color)

    def test_hit_in_lower_priority_profile_with_higher_disabled_profile(self):
        shot26 = self.machine.shots.shot_26

        # posted by profile from any mode
        self.mock_event("shot_26_hit")

        # posted by base profile
        self.mock_event("shot_26_profile_26_hit")
        self.mock_event("shot_26_profile_26_base_one_hit")

        # posted by mode 1 profile
        self.mock_event("shot_26_mode1_shot_26_hit")
        self.mock_event("shot_26_mode1_shot_26_mode1_one_hit")

        # posted by mode 2 profile
        self.mock_event("shot_26_mode2_shot_26_hit")
        self.mock_event("shot_26_mode2_shot_26_mode2_one_hit")

        self.start_game()
        self.machine.modes.mode1.start()
        self.machine.modes.mode2.start()

        self.assertTrue(shot26.profiles[0]['enable'])  # mode 2
        self.assertTrue(shot26.profiles[1]['enable'])  # mode 1
        self.assertTrue(shot26.profiles[2]['enable'])  # base

        # disable the shot in mode 2

        shot26.disable(mode=self.machine.modes.mode2)
        self.advance_time_and_run(.1)

        # check the enable values in the profile table
        self.assertFalse(shot26.profiles[0]['enable'])  # mode 2
        self.assertTrue(shot26.profiles[1]['enable'])  # mode 1
        self.assertTrue(shot26.profiles[2]['enable'])  # base

        # make sure the led is a color from mode 1
        self.assertEqual(list(RGBColor('aliceblue').rgb),
                         self.machine.leds.led_26.hw_driver.current_color)

        self.hit_and_release_switch('switch_26')

        # make sure none of the events from mode 2 posted
        self.assertEqual(0, self._events["shot_26_mode2_shot_26_hit"])
        self.assertEqual(0, self._events[
            "shot_26_mode2_shot_26_mode2_one_hit"])

        # make sure the events from mode 1 posted
        self.assertEqual(1, self._events["shot_26_mode1_shot_26_hit"])
        self.assertEqual(1, self._events[
            "shot_26_mode1_shot_26_mode1_one_hit"])

        # make sure the events from the base mode posted
        self.assertEqual(1, self._events["shot_26_hit"])
        self.assertEqual(1, self._events["shot_26_profile_26_hit"])
        self.assertEqual(1, self._events["shot_26_profile_26_base_one_hit"])

    def test_show_restore_in_mode(self):
        self.start_game()

        self.assertLedColor("led_27", "black")

        self.machine.modes.mode2.start()
        self.advance_time_and_run()

        # step1 red
        self.assertLedColor("led_27", "red")

        self.hit_and_release_switch("switch_27")
        self.advance_time_and_run()

        # step2 orange
        self.assertLedColor("led_27", "orange")

        self.machine.modes.mode2.stop()
        self.advance_time_and_run()

        # mode stopped. led off
        self.assertLedColor("led_27", "black")


        self.machine.modes.mode2.start()
        self.advance_time_and_run()

        # back to step2. orange
        self.assertLedColor("led_27", "orange")

        self.hit_and_release_switch("switch_27")
        self.advance_time_and_run()

        # step3
        self.assertLedColor("led_27", "yellow")

    def test_show_restore_in_mode_start_step(self):
        # same as previous test but with a profile with start steps
        self.start_game()

        self.assertLedColor("led_28", "black")

        self.machine.modes.mode2.start()
        self.advance_time_and_run()

        # step1 red
        self.assertLedColor("led_28", "red")

        self.hit_and_release_switch("switch_28")
        self.advance_time_and_run()

        # step2 orange
        self.assertLedColor("led_28", "orange")

        self.machine.modes.mode2.stop()
        self.advance_time_and_run()

        # mode stopped. led off
        self.assertLedColor("led_28", "black")


        self.machine.modes.mode2.start()
        self.advance_time_and_run()

        # back to step2. orange
        self.assertLedColor("led_28", "orange")

        self.hit_and_release_switch("switch_28")
        self.advance_time_and_run()

        # step3
        self.assertLedColor("led_28", "yellow")