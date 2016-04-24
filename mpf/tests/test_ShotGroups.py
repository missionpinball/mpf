from mock import MagicMock

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestShotGroups(MpfTestCase):

    def getConfigFile(self):
        return 'test_shot_groups.yaml'

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

    def test_disabled_when_no_game(self):
        # all shot group functionality should be disabled if there is not a
        # game in progress. Really we're just making sure this doesn't crash.

        self.machine.events.post('s_rotate_l_active')
        self.advance_time()

        self.hit_and_release_switch("switch_1")
        self.hit_and_release_switch("switch_2")
        self.hit_and_release_switch("switch_3")
        self.hit_and_release_switch("switch_4")

    def test_events_and_complete(self):
        self.start_game()

        self.mock_event("test_group_default_lit_complete")
        self.mock_event("test_group_default_unlit_complete")
        self.mock_event("test_group_default_lit_hit")
        self.mock_event("test_group_default_unlit_hit")
        self.mock_event("test_group_default_hit")
        self.mock_event("test_group_hit")

        self.hit_and_release_switch("switch_1")

        # it should post events. here for the previous(?) profile state
        self.assertEqual(0, self._events['test_group_default_lit_hit'])
        self.assertEqual(1, self._events['test_group_default_unlit_hit'])
        self.assertEqual(1, self._events['test_group_default_hit'])
        self.assertEqual(1, self._events['test_group_hit'])

        self.hit_and_release_switch("switch_1")

        # it posts the opposite state
        self.assertEqual(0, self._events['test_group_default_lit_complete'])
        self.assertEqual(0, self._events['test_group_default_unlit_complete'])
        self.assertEqual(1, self._events['test_group_default_lit_hit'])
        self.assertEqual(1, self._events['test_group_default_unlit_hit'])
        self.assertEqual(2, self._events['test_group_default_hit'])
        self.assertEqual(2, self._events['test_group_hit'])

        self.hit_and_release_switch("switch_2")
        self.hit_and_release_switch("switch_3")
        self.hit_and_release_switch("switch_4")

        self.assertEqual(1, self._events['test_group_default_lit_complete'])
        self.assertEqual(0, self._events['test_group_default_unlit_complete'])
        self.assertEqual(1, self._events['test_group_default_lit_hit'])
        self.assertEqual(4, self._events['test_group_default_unlit_hit'])
        self.assertEqual(5, self._events['test_group_default_hit'])
        self.assertEqual(5, self._events['test_group_hit'])

        self.stop_game()

    def test_rotate(self):
        self.start_game()

        self.mock_event("test_group_default_lit_complete")

        self.assertEqual("unlit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("switch_1")

        self.assertEqual("lit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("unlit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("switch_1")

        self.assertEqual("lit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("unlit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("unlit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("lit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_l")

        self.assertEqual("unlit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("lit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

    def test_shot_group_in_mode(self):
        self.start_game()

        self.hit_and_release_switch("switch_1")

        self.assertEqual("lit", self.machine.shots.shot_1.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_2.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_3.get_profile_by_key('mode', None)[
            'current_state_name'])
        self.assertEqual("unlit", self.machine.shots.shot_4.get_profile_by_key('mode', None)[
            'current_state_name'])

        # Start the mode
        self.machine.modes.mode_shot_groups.start()
        self.advance_time_and_run()

        self.assertEqual("one", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("unlit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("switch_1")
        self.assertEqual("two", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("unlit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_l")
        self.assertEqual("one", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("two", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("lit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_l")
        self.assertEqual("one", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("two", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("unlit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_l")
        self.assertEqual("two", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("unlit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_l")
        self.assertEqual("one", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("two", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("unlit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

        self.hit_and_release_switch("s_rotate_r")
        self.assertEqual("two", self.machine.shots.shot_1.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_2.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("one", self.machine.shots.shot_3.get_profile_by_key('mode', self.machine.modes.mode_shot_groups)[
            'current_state_name'])
        self.assertEqual("unlit",
                         self.machine.shots.shot_4.get_profile_by_key(
                             'mode', None)[
            'current_state_name'])

    def test_rotate_with_shows_in_progress(self):
        self.start_game()
        self.advance_time_and_run()

        # advance the shots a bit

        self.assertEqual(RGBColor('off'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('off'),
            self.machine.leds.led_11.hw_driver.current_color)

        self.hit_and_release_switch('switch_10')
        self.advance_time_and_run()
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('off'),
            self.machine.leds.led_11.hw_driver.current_color)

        self.hit_and_release_switch('switch_10')
        self.advance_time_and_run()
        self.assertEqual(RGBColor('orange'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('off'),
            self.machine.leds.led_11.hw_driver.current_color)

        self.hit_and_release_switch('switch_11')
        self.advance_time_and_run()
        self.assertEqual(RGBColor('orange'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_11.hw_driver.current_color)

        # rotate
        self.machine.events.post('rotate_11_left')
        self.advance_time_and_run()
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('orange'),
            self.machine.leds.led_11.hw_driver.current_color)

        # make sure they don't auto advance since the shows should be set to
        # manual advance
        self.advance_time_and_run()
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('orange'),
            self.machine.leds.led_11.hw_driver.current_color)

        self.advance_time_and_run()
        self.assertEqual(RGBColor('red'),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(RGBColor('orange'),
            self.machine.leds.led_11.hw_driver.current_color)




    def test_no_profile_in_shot_group_uses_profile_from_shot(self):
        pass  # todo

    def test_control_events(self):
        pass

        # test both in base and mode

        # enable_events
        # disable_events
        # reset_events
        # rotate_left_events
        # rotate_right_events
        # enable_rotation_events
        # disable_rotation_events
        # advance_events


    def test_state_names_to_rotate(self):
        pass

    def test_state_names_to_not_rotate(self):
        pass

    def test_rotation_pattern(self):
        pass

    def test_adding_and_removing_from_group(self):
        pass
