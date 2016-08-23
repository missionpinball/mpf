from unittest.mock import MagicMock

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestShotGroups(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'test_shot_groups.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/shots/'

    def test_disabled_when_no_game(self):
        # all shot group functionality should be disabled if there is not a
        # game in progress. Really we're just making sure this doesn't crash.

        self.machine.events.post('s_rotate_l_active')
        self.advance_time_and_run()

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
        # also tests profile from shot_group with no profile in shots
        self.start_game()
        self.advance_time_and_run()

        # advance the shots a bit

        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

        self.hit_and_release_switch('switch_10')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

        self.hit_and_release_switch('switch_10')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

        self.hit_and_release_switch('switch_11')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

        # rotate
        self.machine.events.post('rotate_11_left')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

        # make sure they don't auto advance since the shows should be set to
        # manual advance
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_10.hw_driver.current_color)
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_11.hw_driver.current_color)

    def test_no_profile_in_shot_group_uses_profile_from_shot(self):
        self.start_game()
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_30.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_31.hw_driver.current_color)

        self.hit_and_release_switch('switch_30')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_30.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_31.hw_driver.current_color)

        self.hit_and_release_switch('switch_30')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_30.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_31.hw_driver.current_color)

        self.hit_and_release_switch('switch_31')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_30.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_31.hw_driver.current_color)

    def test_control_events(self):
        # tests control events at the shot_group level

        shot32 = self.machine.shots.shot_32
        shot33 = self.machine.shots.shot_33
        group32 = self.machine.shot_groups.shot_group_32

        self.mock_event("shot_32_hit")
        self.mock_event("shot_33_hit")
        self.mock_event("shot_group_32_hit")

        self.start_game()

        # Since this shot has custom enable events, it should not be enabled on
        # game start
        self.assertFalse(shot32.enabled)
        self.assertFalse(shot33.enabled)
        self.assertFalse(group32.enabled)

        # test enabling via event
        self.machine.events.post('group32_enable')
        self.advance_time_and_run()

        self.assertTrue(shot32.enabled)
        self.assertTrue(shot33.enabled)
        self.assertTrue(group32.enabled)

        # test advance event
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_33.hw_driver.current_color)

        self.machine.events.post('group32_advance')
        self.advance_time_and_run()
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'red')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_33.hw_driver.current_color)

        # test reset event
        self.machine.events.post('group32_reset')
        self.advance_time_and_run()
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_33.hw_driver.current_color)

        # test rotate without rotation enabled
        shot32.advance()
        self.advance_time_and_run()
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_33.hw_driver.current_color)
        self.assertFalse(group32.rotation_enabled)

        self.machine.events.post('group32_rotate')
        self.advance_time_and_run()
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_33.hw_driver.current_color)

        # test rotation enable
        self.machine.events.post('group32_enable_rotation')
        self.advance_time_and_run()
        self.assertTrue(group32.rotation_enabled)

        # test that rotate works now
        self.machine.events.post('group32_rotate')
        self.advance_time_and_run()
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'red')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_33.hw_driver.current_color)

        # test disable rotation
        self.machine.events.post('group32_disable_rotation')
        self.advance_time_and_run()
        self.assertFalse(group32.rotation_enabled)

        # test that rotate works now
        self.machine.events.post('group32_rotate')
        self.advance_time_and_run()

        # test that rotate did not happen
        self.assertEqual(shot32.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot33.profiles[0]['current_state_name'], 'red')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_32.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_33.hw_driver.current_color)

        # test disable event
        self.machine.events.post('group32_disable')
        self.advance_time_and_run()
        self.assertFalse(shot32.enabled)
        self.assertFalse(shot33.enabled)
        self.assertFalse(group32.enabled)

    def test_state_names_to_rotate(self):
        shot34 = self.machine.shots.shot_34
        shot35 = self.machine.shots.shot_35
        shot36 = self.machine.shots.shot_36
        group34 = self.machine.shot_groups.shot_group_34

        self.start_game()

        # create some mixed states to test
        shot34.advance()
        shot35.advance(4)  # also tests profile base show advances properly
        self.advance_time_and_run()
        self.assertEqual(shot34.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot35.profiles[0]['current_state_name'], 'green')
        self.assertEqual(shot36.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_34.hw_driver.current_color)
        self.assertEqual(list(RGBColor('green').rgb),
            self.machine.leds.led_35.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_36.hw_driver.current_color)

        # rotate, only the red and green states should be rotated
        group34.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot34.profiles[0]['current_state_name'], 'green')
        self.assertEqual(shot35.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot36.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('green').rgb),
            self.machine.leds.led_34.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_35.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_36.hw_driver.current_color)

    def test_state_names_to_not_rotate(self):
        shot37 = self.machine.shots.shot_37
        shot38 = self.machine.shots.shot_38
        shot39 = self.machine.shots.shot_39
        group37 = self.machine.shot_groups.shot_group_37

        self.start_game()

        # create some mixed states to test
        shot37.advance()
        shot38.advance(2)
        self.advance_time_and_run()
        self.assertEqual(shot37.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot38.profiles[0]['current_state_name'], 'orange')
        self.assertEqual(shot39.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_37.hw_driver.current_color)
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_38.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_39.hw_driver.current_color)

        # rotate, only the red and green states should be rotated
        group37.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot37.profiles[0]['current_state_name'], 'orange')
        self.assertEqual(shot38.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot39.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('orange').rgb),
            self.machine.leds.led_37.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_38.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_39.hw_driver.current_color)

    def test_rotation_pattern(self):
        shot40 = self.machine.shots.shot_40
        shot41 = self.machine.shots.shot_41
        shot42 = self.machine.shots.shot_42
        group40 = self.machine.shot_groups.shot_group_40

        self.start_game()

        shot40.advance()
        self.advance_time_and_run()
        self.assertEqual(shot40.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot41.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot42.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_40.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_41.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_42.hw_driver.current_color)

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot41.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot42.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_40.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_41.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_42.hw_driver.current_color)

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot41.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot42.profiles[0]['current_state_name'], 'red')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_40.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_41.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_42.hw_driver.current_color)

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot41.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot42.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_40.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_41.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_42.hw_driver.current_color)

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot41.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot42.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_40.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_41.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_42.hw_driver.current_color)

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(shot41.profiles[0]['current_state_name'], 'red')
        self.assertEqual(shot42.profiles[0]['current_state_name'], 'unlit')
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_40.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
            self.machine.leds.led_41.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.led_42.hw_driver.current_color)

    def test_block_in_shot_group_profile(self):
        self.mock_event('shot_43_hit')
        self.mock_event('shot_43_default_hit')
        self.mock_event('shot_43_default_unlit_hit')
        self.mock_event('shot_43_profile_43_hit')
        self.mock_event('shot_43_profile_43_one_hit')

        self.start_game()
        self.machine.modes.mode_shot_groups.start()

        self.hit_and_release_switch('switch_43')

        # events from the mode should be posted
        self.assertEqual(1, self._events['shot_43_hit'])
        self.assertEqual(1, self._events['shot_43_profile_43_hit'])
        self.assertEqual(1, self._events['shot_43_profile_43_one_hit'])

        # shot group in mode config is set to block, so base events should not
        # have been posted
        self.assertEqual(0, self._events['shot_43_default_unlit_hit'])
        self.assertEqual(0, self._events['shot_43_default_hit'])

    def test_profile_in_shot_group_overwrites_profile_in_shot(self):
        self.mock_event('shot_45_rainbow_hit')  # from the shot config
        self.mock_event('shot_45_rainbow_no_hold_hit')  # from the shot_group

        self.start_game()

        self.hit_and_release_switch('switch_45')

        self.assertEqual(0, self._events['shot_45_rainbow_hit'])
        self.assertEqual(1, self._events['shot_45_rainbow_no_hold_hit'])

        # also test this with a shot profile in base and a shot_group
        # profile in a higher mode
        # todo

    def test_control_events_in_mode(self):
        pass  # todo

    def test_gas(self):
        self.start_game()

        self.machine.modes.mode_shot_groups.start()
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_g.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_a.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_s.hw_driver.current_color)

        self.hit_and_release_switch('s_gas_g')
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('white').rgb),
            self.machine.leds.l_gas_g.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_a.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_s.hw_driver.current_color)

        self.machine.events.post('s_upper_left_flipper_active')
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_g.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
            self.machine.leds.l_gas_a.hw_driver.current_color)
        self.assertEqual(list(RGBColor('white').rgb),
            self.machine.leds.l_gas_s.hw_driver.current_color)

    def test_profile_on_second_ball(self):
        self.start_game()

        self.assertEqual(0, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.l_special_right.hw_driver.current_brightness)

        shot = self.machine.shots.lane_special_left

        self.assertEqual('prof_toggle', shot.profiles[0]['profile'])
        self.assertEqual('unlit_toggle', shot.profiles[0]['current_state_name'])

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertEqual(255, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual('lit_toggle', shot.profiles[0]['current_state_name'])

        # toggle off
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual('unlit_toggle', shot.profiles[0]['current_state_name'])

        # drain ball and try on the second ball
        self.drain_ball()
        self.assertBallNumber(2)

        self.assertEqual('prof_toggle', shot.profiles[0]['profile'])
        self.assertEqual('unlit_toggle', shot.profiles[0]['current_state_name'])

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertEqual(255, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual('lit_toggle', shot.profiles[0]['current_state_name'])

        # toggle off
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual('unlit_toggle', shot.profiles[0]['current_state_name'])

        self.drain_ball()
        self.assertBallNumber(3)

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertEqual(255, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual('lit_toggle', shot.profiles[0]['current_state_name'])

        # toggle off
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.lights.l_special_left.hw_driver.current_brightness)
        self.assertEqual('unlit_toggle', shot.profiles[0]['current_state_name'])

    def test_profile_in_mode(self):
        self.start_game()
        self.advance_time_and_run()
        self.assertEqual(0, self.machine.lights.l_special_right.hw_driver.current_brightness)
        shot = self.machine.shots.lane_special_right

        # toggle on
        self.hit_and_release_switch("s_special_right")
        self.advance_time_and_run(.1)
        self.assertEqual(255, self.machine.lights.l_special_right.hw_driver.current_brightness)
        self.assertEqual('lit2', shot.profiles[0]['current_state_name'])

        # toggle off
        self.hit_and_release_switch("s_special_right")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.lights.l_special_right.hw_driver.current_brightness)
        self.assertEqual('unlit2', shot.profiles[0]['current_state_name'])

        self.assertEqual('prof_toggle2', shot.profiles[0]['profile'])
        self.assertEqual('unlit2', shot.profiles[0]['current_state_name'])

        # toggle on
        self.hit_and_release_switch("s_special_right")
        self.advance_time_and_run(.1)
        self.assertEqual(255, self.machine.lights.l_special_right.hw_driver.current_brightness)
        self.assertEqual('lit2', shot.profiles[0]['current_state_name'])

        # toggle off
        self.hit_and_release_switch("s_special_right")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.lights.l_special_right.hw_driver.current_brightness)
        self.assertEqual('unlit2', shot.profiles[0]['current_state_name'])
