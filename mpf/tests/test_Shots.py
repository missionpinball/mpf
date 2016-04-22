from mock import MagicMock

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestShots(MpfTestCase):

    def getConfigFile(self):
        return 'test_shots.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/shots/'

    def start_game(self):
        # shots only work in games so we have to do this a lot
        self.machine.playfield.add_ball = MagicMock()
        self.machine.events.post('game_start')
        self.advance_time_and_run()
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

        self.assertNotIn('mode1_shot_1', self.machine.shots)

        # Start the mode and make sure those shots load
        self.machine.modes.mode1.start()
        self.advance_time_and_run()
        self.assertIn('mode1_shot_1', self.machine.shots)

        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

        # Stop the mode and make sure those shots go away
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()
        self.assertNotIn('mode1_shot_1', self.machine.shots)

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
        self.machine.switch_controller.process_switch('switch_1', 1)
        self.machine.switch_controller.process_switch('switch_1', 0)
        self.advance_time_and_run()
        self.shot_1_hit.assert_not_called()

        self.start_game()

        # hit shot_1, test all three event variations
        self.machine.switch_controller.process_switch('switch_1', 1)
        self.machine.switch_controller.process_switch('switch_1', 0)
        self.advance_time_and_run()

        self.shot_1_hit.assert_called_once_with(profile='default',
                                                state='unlit')
        self.shot_1_default_hit.assert_called_once_with(profile='default',
                                                        state='unlit')
        self.shot_1_default_unlit_hit.assert_called_once_with(
                profile='default', state='unlit')

        # hit the mode shot and make sure it doesn't fire
        self.machine.switch_controller.process_switch('switch_3', 1)
        self.machine.switch_controller.process_switch('switch_3', 0)
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

        # Start the mode
        self.machine.modes.mode1.start()
        self.advance_time_and_run()

        # hit the mode shot and make sure it was called
        self.machine.switch_controller.process_switch('switch_3', 1)
        self.machine.switch_controller.process_switch('switch_3', 0)
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_called_once_with(profile='default',
                                                      state='unlit')

        # stop the mode
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()

        # hit the mode shot and make sure it was not called
        self.mode1_shot_1_hit = MagicMock()
        self.machine.switch_controller.process_switch('switch_3', 1)
        self.machine.switch_controller.process_switch('switch_3', 0)
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

        # stop the game (should not crash)
        self.stop_game()

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

    def test_profile_advancing_no_loop(self):
        self.start_game()

        # unlit and two states in the beginning
        self.assertEqual(2, len(self.machine.shots.shot_1.active_settings['settings']['states']))
        self.assertEqual("unlit", self.machine.shots.shot_1.active_settings['current_state_name'])

        # one hit and it lits
        self.hit_and_release_switch("switch_1")
        self.assertEqual("lit", self.machine.shots.shot_1.active_settings['current_state_name'])
        self.assertEqual(1, self.machine.game.player["shot_1_default"])

        # it stays lit
        self.hit_and_release_switch("switch_1")
        self.assertEqual("lit", self.machine.shots.shot_1.active_settings['current_state_name'])
        self.assertEqual(1, self.machine.game.player["shot_1_default"])

    def test_profile_advancing_with_loop(self):
        self.start_game()

        self.assertEqual(3, len(self.machine.shots.shot_2.active_settings['settings']['states']))

        self.assertEqual("one", self.machine.shots.shot_2.active_settings['current_state_name'])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("two", self.machine.shots.shot_2.active_settings['current_state_name'])
        self.assertEqual(1, self.machine.game.player["shot_2_three_states_loop"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("three", self.machine.shots.shot_2.active_settings['current_state_name'])
        self.assertEqual(2, self.machine.game.player["shot_2_three_states_loop"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("one", self.machine.shots.shot_2.active_settings['current_state_name'])
        self.assertEqual(0, self.machine.game.player["shot_2_three_states_loop"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("two", self.machine.shots.shot_2.active_settings['current_state_name'])
        self.assertEqual(1, self.machine.game.player["shot_2_three_states_loop"])

    def test_default_show_light(self):
        self.start_game()
        self.assertEqual(0,
            self.machine.lights.light_1.hw_driver.current_brightness)

        self.hit_and_release_switch("switch_5")
        self.advance_time_and_run()
        self.assertEqual(255,
            self.machine.lights.light_1.hw_driver.current_brightness)

    def test_default_show_lights(self):
        self.start_game()
        self.assertEqual(0,
            self.machine.lights.light_1.hw_driver.current_brightness)
        self.assertEqual(0,
            self.machine.lights.light_2.hw_driver.current_brightness)

        self.hit_and_release_switch("switch_6")
        self.advance_time_and_run()
        self.assertEqual(255,
            self.machine.lights.light_1.hw_driver.current_brightness)
        self.assertEqual(255,
            self.machine.lights.light_2.hw_driver.current_brightness)

    def test_default_show_led(self):
        self.start_game()
        self.assertEqual(RGBColor('off'),
                         self.machine.leds.led_1.hw_driver.current_color)

        self.hit_and_release_switch("switch_7")
        self.advance_time_and_run()

        self.assertEqual(RGBColor('white'),
                         self.machine.leds.led_1.hw_driver.current_color)

    def test_default_show_leds(self):
        self.start_game()
        self.assertEqual(RGBColor('off'),
                         self.machine.leds.led_1.hw_driver.current_color)
        self.assertEqual(RGBColor('off'),
                         self.machine.leds.led_2.hw_driver.current_color)

        self.hit_and_release_switch("switch_8")
        self.advance_time_and_run()

        self.assertEqual(RGBColor('white'),
                         self.machine.leds.led_1.hw_driver.current_color)
        self.assertEqual(RGBColor('white'),
                         self.machine.leds.led_2.hw_driver.current_color)

    def test_show_in_shot_profile_root(self):
        self.start_game()
        self.advance_time_and_run()
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_3.hw_driver.current_color)

        # make sure the show is not auto advancing
        self.advance_time_and_run(5)
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_3.hw_driver.current_color)

        self.advance_time_and_run(5)
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_3.hw_driver.current_color)

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertEqual(RGBColor('orange'),
            self.machine.leds.led_3.hw_driver.current_color)

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertEqual(RGBColor('yellow'),
            self.machine.leds.led_3.hw_driver.current_color)

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertEqual(RGBColor('green'),
            self.machine.leds.led_3.hw_driver.current_color)

        # show's over, make sure it stays on green

        self.advance_time_and_run(5)
        self.assertEqual(RGBColor('green'),
            self.machine.leds.led_3.hw_driver.current_color)

    def test_show_in_step(self):
        self.start_game()
        self.advance_time_and_run()

        show1_colors = (RGBColor('red'), RGBColor('orange'),
                        RGBColor('yellow'), RGBColor('green'))

        show2_colors = (RGBColor('aliceblue'), RGBColor('antiquewhite'),
                        RGBColor('aquamarine'), RGBColor('azure'))

        self.assertIn(self.machine.leds.led_4.hw_driver.current_color,
                      show1_colors)

        self.hit_and_release_switch('switch_10')
        self.advance_time_and_run()
        self.assertIn(self.machine.leds.led_4.hw_driver.current_color,
                      show2_colors)

        self.hit_and_release_switch('switch_10')
        self.advance_time_and_run()
        self.assertIn(self.machine.leds.led_4.hw_driver.current_color,
                      show1_colors)

    def test_combined_show_in_profile_root_and_step(self):
        pass

    def test_multiple_switches(self):
        pass

    def test_switch_sequence(self):
        pass

        # include cancel switch, delay switch, time

    def test_control_events(self):
        pass

        # enable_events
        # disable_events
        # reset_events
        # hit_events
        # advance_events
        # remove_active_profile_events

        # shot groups
        # enable_events
        # disable_events
        # reset_events
        # rotate_left_events
        # rotate_right_events
        # enable_rotation_events
        # disable_rotation_events
        # advance_events
        # remove_active_profile_events

    def test_shot_profiles(self):
        pass
        # loop
        # state_names_to_rotate
        # state_names_to_not_rotate
        # rotation_pattern
        # player_variable
        # show_when_disabled
        # block
        # states (with various show params and tokens)
