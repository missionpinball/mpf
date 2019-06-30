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
        self.mock_event("test_group_complete")
        self.mock_event("test_group_hit")

        self.start_game()

        # it should post events. here for the initial profile state (on mode start)
        self.assertEventNotCalled("test_group_hit")
        self.assertEventCalledWith("test_group_complete", state="unlit")
        self.mock_event("test_group_complete")
        self.mock_event("test_group_hit")
        self.assertPlaceholderEvaluates("unlit", "device.shot_groups.test_group.common_state")

        self.hit_and_release_switch("switch_1")

        # it posts nothing because the the there is no common state
        self.assertEventCalled("test_group_hit")
        self.assertEventNotCalled("test_group_complete")

        self.hit_and_release_switch("switch_2")
        self.assertPlaceholderEvaluates(None, "device.shot_groups.test_group.common_state")
        self.hit_and_release_switch("switch_3")
        self.hit_and_release_switch("switch_4")

        self.assertEventCalled("test_group_hit")
        self.assertEventCalledWith("test_group_complete", state="lit")
        self.assertPlaceholderEvaluates("lit", "device.shot_groups.test_group.common_state")

        self.stop_game()

    def test_rotate(self):
        self.start_game()

        self.assertEqual("unlit", self.machine.shots.shot_1.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_2.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_3.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("switch_1")

        self.assertEqual("lit", self.machine.shots.shot_1.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_2.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_3.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("unlit", self.machine.shots.shot_1.state_name)
        self.assertEqual("lit", self.machine.shots.shot_2.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_3.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("switch_1")

        self.assertEqual("lit", self.machine.shots.shot_1.state_name)
        self.assertEqual("lit", self.machine.shots.shot_2.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_3.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("unlit", self.machine.shots.shot_1.state_name)
        self.assertEqual("lit", self.machine.shots.shot_2.state_name)
        self.assertEqual("lit", self.machine.shots.shot_3.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("unlit", self.machine.shots.shot_1.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_2.state_name)
        self.assertEqual("lit", self.machine.shots.shot_3.state_name)
        self.assertEqual("lit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("s_rotate_r")

        self.assertEqual("lit", self.machine.shots.shot_1.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_2.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_3.state_name)
        self.assertEqual("lit", self.machine.shots.shot_4.state_name)

        self.hit_and_release_switch("s_rotate_l")

        self.assertEqual("unlit", self.machine.shots.shot_1.state_name)
        self.assertEqual("unlit", self.machine.shots.shot_2.state_name)
        self.assertEqual("lit", self.machine.shots.shot_3.state_name)
        self.assertEqual("lit", self.machine.shots.shot_4.state_name)

    def test_profile_from_shot(self):
        self.start_game()
        self.advance_time_and_run()

        self.assertLightColor("led_30", 'off')
        self.assertLightColor("led_31", 'off')

        self.hit_and_release_switch('switch_30')
        self.advance_time_and_run()
        self.assertLightColor("led_30", 'red')
        self.assertLightColor("led_31", 'off')

        self.hit_and_release_switch('switch_30')
        self.advance_time_and_run()
        self.assertLightColor("led_30", 'orange')
        self.assertLightColor("led_31", 'off')

        self.hit_and_release_switch('switch_31')
        self.advance_time_and_run()
        self.assertLightColor("led_30", 'orange')
        self.assertLightColor("led_31", 'red')

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

        # test enabling via event
        self.machine.events.post('group32_enable')
        self.advance_time_and_run()

        self.assertTrue(shot32.enabled)
        self.assertTrue(shot33.enabled)

        # test disabling via event
        self.machine.events.post('group32_disable')
        self.advance_time_and_run()

        self.assertFalse(shot32.enabled)
        self.assertFalse(shot33.enabled)

        # test enabling via event
        self.machine.events.post('group32_enable')
        self.advance_time_and_run()

        self.assertTrue(shot32.enabled)
        self.assertTrue(shot33.enabled)

        # test rotate without rotation enabled
        shot32.advance()
        self.advance_time_and_run()
        self.assertEqual(shot32.state_name, 'red')
        self.assertEqual(shot33.state_name, 'unlit')
        self.assertLightColor("led_32", 'red')
        self.assertLightColor("led_33", 'off')
        self.assertFalse(group32.rotation_enabled)
        self.assertPlaceholderEvaluates(False, "device.shot_groups.shot_group_32.rotation_enabled")

        self.machine.events.post('group32_rotate')
        self.advance_time_and_run()
        self.assertEqual(shot32.state_name, 'red')
        self.assertEqual(shot33.state_name, 'unlit')
        self.assertLightColor("led_32", 'red')
        self.assertLightColor("led_33", 'off')

        # test rotation enable
        self.machine.events.post('group32_enable_rotation')
        self.advance_time_and_run()
        self.assertTrue(group32.rotation_enabled)
        self.assertPlaceholderEvaluates(True, "device.shot_groups.shot_group_32.rotation_enabled")

        # test that rotate works now
        self.machine.events.post('group32_rotate_left')
        self.advance_time_and_run()
        self.assertEqual(shot32.state_name, 'unlit')
        self.assertEqual(shot33.state_name, 'red')
        self.assertLightColor("led_32", 'off')
        self.assertLightColor("led_33", 'red')

        # test disable rotation
        self.machine.events.post('group32_disable_rotation')
        self.advance_time_and_run()
        self.assertFalse(group32.rotation_enabled)

        # test that rotate works now
        self.machine.events.post('group32_rotate_left')
        self.advance_time_and_run()

        # test that rotate did not happen
        self.assertEqual(shot32.state_name, 'unlit')
        self.assertEqual(shot33.state_name, 'red')
        self.assertLightColor("led_32", 'off')
        self.assertLightColor("led_33", 'red')

        # test reset
        # test enabling via event
        self.machine.events.post('group32_reset')
        self.advance_time_and_run()

        self.assertTrue(shot32.enabled)
        self.assertTrue(shot33.enabled)
        self.assertEqual(shot32.state_name, 'unlit')
        self.assertEqual(shot33.state_name, 'unlit')
        self.assertLightColor("led_32", 'off')
        self.assertLightColor("led_33", 'off')

        # test restart
        # first advance and disable
        shot32.advance()
        shot33.advance()
        shot32.disable()
        shot33.disable()
        self.assertFalse(shot32.enabled)
        self.assertFalse(shot33.enabled)
        self.assertEqual(shot32.state_name, 'red')
        self.assertEqual(shot33.state_name, 'red')
        # ensure all shots are enabled and at the first state
        self.machine.events.post('group32_restart')
        self.advance_time_and_run()
        self.assertTrue(shot32.enabled)
        self.assertTrue(shot33.enabled)
        self.assertEqual(shot32.state_name, 'unlit')
        self.assertEqual(shot33.state_name, 'unlit')

    def test_rotation_pattern(self):
        shot40 = self.machine.shots.shot_40
        shot41 = self.machine.shots.shot_41
        shot42 = self.machine.shots.shot_42
        group40 = self.machine.shot_groups.shot_group_40

        self.start_game()

        shot40.advance()
        self.advance_time_and_run()
        self.assertEqual(shot40.state_name, 'red')
        self.assertEqual(shot41.state_name, 'unlit')
        self.assertEqual(shot42.state_name, 'unlit')
        self.assertLightColor("led_40", 'red')
        self.assertLightColor("led_41", 'off')
        self.assertLightColor("led_42", 'off')

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.state_name, 'unlit')
        self.assertEqual(shot41.state_name, 'red')
        self.assertEqual(shot42.state_name, 'unlit')
        self.assertLightColor("led_40", 'off')
        self.assertLightColor("led_41", 'red')
        self.assertLightColor("led_42", 'off')

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.state_name, 'unlit')
        self.assertEqual(shot41.state_name, 'unlit')
        self.assertEqual(shot42.state_name, 'red')
        self.assertLightColor("led_40", 'off')
        self.assertLightColor("led_41", 'off')
        self.assertLightColor("led_42", 'red')

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.state_name, 'unlit')
        self.assertEqual(shot41.state_name, 'red')
        self.assertEqual(shot42.state_name, 'unlit')
        self.assertLightColor("led_40", 'off')
        self.assertLightColor("led_41", 'red')
        self.assertLightColor("led_42", 'off')

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.state_name, 'red')
        self.assertEqual(shot41.state_name, 'unlit')
        self.assertEqual(shot42.state_name, 'unlit')
        self.assertLightColor("led_40", 'red')
        self.assertLightColor("led_41", 'off')
        self.assertLightColor("led_42", 'off')

        group40.rotate()
        self.advance_time_and_run()
        self.assertEqual(shot40.state_name, 'unlit')
        self.assertEqual(shot41.state_name, 'red')
        self.assertEqual(shot42.state_name, 'unlit')
        self.assertLightColor("led_40", 'off')
        self.assertLightColor("led_41", 'red')
        self.assertLightColor("led_42", 'off')

    def test_profile_on_second_ball(self):
        self.start_game()

        self.assertLightChannel("l_special_left", 0)
        self.assertLightChannel("l_special_right", 0)

        shot = self.machine.shots.lane_special_left

        self.assertEqual('unlit_toggle', shot.state_name)

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 255)
        self.assertEqual('lit_toggle', shot.state_name)

        # toggle off
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 0)
        self.assertEqual('unlit_toggle', shot.state_name)

        # drain ball and try on the second ball
        self.drain_all_balls()
        self.assertBallNumber(2)

        self.assertEqual('unlit_toggle', shot.state_name)

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 255)
        self.assertEqual('lit_toggle', shot.state_name)

        # toggle off
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 0)
        self.assertEqual('unlit_toggle', shot.state_name)

        self.drain_all_balls()
        self.assertBallNumber(3)

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 255)
        self.assertEqual('lit_toggle', shot.state_name)

        # toggle off
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 0)
        self.assertEqual('unlit_toggle', shot.state_name)

        # toggle on
        self.hit_and_release_switch("s_special_left")
        self.advance_time_and_run(.1)
        self.assertLightChannel("l_special_left", 255)
        self.assertEqual('lit_toggle', shot.state_name)

        self.drain_all_balls()
        self.assertGameIsNotRunning()

        # shot should turn off after game
        self.assertLightChannel("l_special_left", 0)
