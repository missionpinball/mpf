"""Test achievements."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestAchievement(MpfFakeGameTestCase):
    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/achievement/'

    def test_enable_when_all_done(self):
        self.start_game()
        self.mock_event("achievement_mode1_a1_state_selected")
        self.mock_event("achievement_mode1_a2_state_selected")
        self.mock_event("enable_all")
        self.advance_time_and_run()
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.assertEventCalled("enable_all", times=1)
        self.post_event("stop_mode1")

        self.post_event("start_all")
        self.post_event("complete_all")
        self.assertEqual("completed", self.machine.achievements['mode1_a1'].state)
        self.assertEqual("completed", self.machine.achievements['mode1_a2'].state)

        self.assertEventCalled("enable_all", times=1)
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.assertEventCalled("enable_all", times=2)

    def test_two_players_restart_with_keep(self):
        self.mock_event("achievement_achievement1_state_disabled")
        self.mock_event("achievement_achievement1_state_enabled")
        self.mock_event("achievement_achievement1_state_started")
        self.mock_event("achievement_achievement1_state_stopped")
        self.mock_event("achievement_achievement1_state_completed")

        achievement = self.machine.achievements['achievement1']

        self.assertEqual(None, achievement._show)

        self.start_two_player_game()
        self.assertModeRunning('base')
        self.advance_time_and_run(10)

        _, sub1 = self.machine.placeholder_manager.build_raw_template(
            "device.achievements.achievement1.state").evaluate_and_subscribe([])
        _, sub2 = self.machine.placeholder_manager.build_raw_template(
            "device.achievements.achievement2.state").evaluate_and_subscribe([])

        # start disabled
        self.assertEqual("achievement1_disabled", achievement._show.name)
        self.assertEqual("disabled", achievement.state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(0, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(0, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_stopped'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        # should not start
        self.post_event("achievement1_start")
        self.assertEqual("disabled", achievement.state)
        self.assertPlaceholderEvaluates("disabled", "device.achievements.achievement1.state")
        self.assertPlaceholderEvaluates("disabled", "device.achievements.achievement2.state")
        self.assertFalse(sub1.done())
        self.assertFalse(sub2.done())

        # enable
        self.post_event("achievement1_enable")
        self.assertEqual("enabled", achievement.state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(0, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertPlaceholderEvaluates("enabled", "device.achievements.achievement1.state")
        self.assertEqual("achievement1_enabled", achievement._show.name)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_enabled']['restore'])
        self.assertTrue(sub1.done())
        self.assertFalse(sub2.done())

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement.state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertPlaceholderEvaluates("started", "device.achievements.achievement1.state")
        self.assertEqual("achievement1_started", achievement._show.name)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_started']['restore'])

        _, sub1 = self.machine.placeholder_manager.build_raw_template(
            "device.achievements.achievement1.state").evaluate_and_subscribe([])

        self.drain_all_balls()

        self.assertPlayerNumber(2)
        self.assertBallNumber(1)
        self.assertEqual("achievement1_disabled", achievement._show.name)
        self.assertEqual("disabled", achievement.state)
        self.assertPlaceholderEvaluates("disabled", "device.achievements.achievement1.state")
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])
        self.assertTrue(sub1.done())

        self.post_event("achievement1_enable")
        self.assertEqual("achievement1_enabled", achievement._show.name)
        self.assertEqual("enabled", achievement.state)

        _, sub1 = self.machine.placeholder_manager.build_raw_template(
            "device.achievements.achievement1.state").evaluate_and_subscribe([])

        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.assertEqual("achievement1_started", achievement._show.name)
        self.assertEqual("started", achievement.state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_started']['restore'])
        self.assertTrue(sub1.done())

        self.post_event("achievement1_complete")
        self.assertEqual("achievement1_completed", achievement._show.name)
        self.assertEqual("completed", achievement.state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_completed']['restore'])

        self.post_event("achievement1_enable")
        self.post_event("achievement1_disable")
        self.post_event("achievement1_stop")
        self.assertEqual("completed", achievement.state)

        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        self.assertEqual("achievement1_enabled", achievement._show.name)
        self.assertEqual("enabled", achievement.state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_enabled']['restore'])

        self.post_event("achievement1_disable")
        self.assertEqual("disabled", achievement.state)

        self.post_event("achievement1_enable")
        self.assertEqual("enabled", achievement.state)

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement.state)

        self.post_event("achievement1_stop")
        self.assertEqual("stopped", achievement.state)
        self.assertEqual("achievement1_stopped", achievement._show.name)

        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.assertEqual("achievement1_completed", achievement._show.name)
        self.assertEqual("completed", achievement.state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_completed']['restore'])

        self.post_event("achievement1_reset")
        self.assertEqual("achievement1_disabled", achievement._show.name)
        self.assertEqual("disabled", achievement.state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        self.assertEqual("stopped", achievement.state)
        self.assertEqual("achievement1_stopped", achievement._show.name)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_stopped']['restore'])

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement.state)

        self.drain_all_balls()
        self.assertGameIsNotRunning()

        self.assertEqual(None, achievement._show)

    def test_one_player_no_restart(self):
        self.mock_event("test_event")
        self.mock_event("test_event2")
        achievement = self.machine.achievements['achievement2']
        self.assertEqual(None, achievement._show)
        self.assertLightColor('led1', 'off')

        self.start_game()

        # enable
        self.post_event('achievement2_enable', 1)

        self.assertEqual("achievement2_enabled", achievement._show.name)
        self.assertEqual("enabled", achievement.state)
        self.assertLightColor('led1', 'yellow')

        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        self.assertEqual(None, achievement._show)
        self.assertEqual("disabled", achievement.state)
        self.assertLightColor('led1', 'off')

        self.post_event("achievement2_enable", 2)
        self.assertEqual("enabled", achievement.state)
        self.assertLightColor('led1', 'yellow')

        self.assertEqual(0, self._events['test_event'])
        self.assertEqual(0, self._events['test_event2'])

        self.post_event("achievement2_start", 2)
        self.assertEqual("achievement2_started", achievement._show.name)
        self.assertEqual("started", achievement.state)
        self.assertLightColor('led1', 'green')

        self.assertEqual(1, self._events['test_event'])
        self.assertEqual(1, self._events['test_event2'])
        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.assertEqual("stopped", achievement.state)
        self.assertEqual(None, achievement._show)
        self.assertLightColor('led1', 'off')  # no show when stopped

        # restart after stop is False
        self.post_event("achievement2_start", 2)
        self.assertEqual("stopped", achievement.state)
        self.assertLightColor('led1', 'off')

    def test_control_events_in_mode(self):
        baseMode = self.machine.modes["base"]
        ach = self.machine.achievements['achievement7']
        group = self.machine.achievement_groups['group1']

        # The custom behavior is unique to mode devices _without_ enable_events
        self.assertFalse(ach.config['enable_events'])
        self.assertFalse(group.config['enable_events'])
        # Assert that the achievement does not add mode event handlers
        self.assertEqual(baseMode.event_handlers, set())
        ach.add_control_events_in_mode(mode=baseMode)
        self.assertEqual(baseMode.event_handlers, set())
        # Assert that achievement groups do add event handlers
        group.add_control_events_in_mode(mode=baseMode)
        self.assertEqual(len(baseMode.event_handlers), 1)

    def test_group_select(self):

        a4 = self.machine.achievements['achievement4']
        a5 = self.machine.achievements['achievement5']
        a6 = self.machine.achievements['achievement6']
        g2 = self.machine.achievement_groups["group2"]

        self.start_game()

        self.assertFalse(g2.enabled)
        self.assertEqual("disabled", a4.state)
        self.assertEqual("disabled", a5.state)
        self.assertEqual("disabled", a6.state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'off')
        self.assertLightColor('led6', 'off')

        # achievements are disabled, should select none

        self.post_event('group2_random', 2)

        enabled_achievements = [x for x in (a4, a5, a6) if x.state == 'enabled']
        self.assertEqual(len(enabled_achievements), 0)

        # enable the achievements and try again, but group is disabled

        a4.enable()
        a5.enable()
        a6.enable()

        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.advance_time_and_run(1)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        self.post_event('group2_random', 2)

        selected_achievements = [x for x in (a4, a5, a6) if x.state == 'selected']
        self.assertEqual(len(selected_achievements), 0)

        # now enable the group and it should work

        self.post_event('group2_enable', 2)
        self.assertTrue(g2._enabled)
        self.assertLightColors('led2', ['red', 'blue'], 1, .09)  # group led

        self.post_event('group2_random', 2)
        selected_achievements = [x for x in (a4, a5, a6) if x.selected]
        self.assertEqual(len(selected_achievements), 1)

        # group enabled, but individual members disabled, should not work

        a4.disable()
        a5.disable()
        a6.disable()
        self.advance_time_and_run(1)

        self.assertEqual("disabled", a4.state)
        self.assertEqual("disabled", a5.state)
        self.assertEqual("disabled", a6.state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'off')
        self.assertLightColor('led6', 'off')

        self.post_event('group2_random')
        selected_achievements = [x for x in (a4, a5, a6) if x.state == 'selected']
        self.assertEqual(len(selected_achievements), 0)

    def test_rotation_when_all_complete(self):
        a14 = self.machine.achievements['achievement14']
        a15 = self.machine.achievements['achievement15']
        a16 = self.machine.achievements['achievement16']
        g4 = self.machine.achievement_groups["group4"]
        g4.enable()

        self.start_game()
        # complete all achievements
        a14.enable()
        a15.enable()
        a16.enable()
        a14.start()
        a15.start()
        a16.start()
        a14.complete()
        a14.complete()
        a15.complete()
        a16.complete()
        self.advance_time_and_run(.1)

        self.assertFalse(g4.enabled)
        self.advance_time_and_run()
        self.assertEqual("completed", a14.state)
        self.assertEqual("completed", a15.state)
        self.assertEqual("completed", a16.state)
        # rotate should not crash
        self.post_event('group4_rotate_right')

    def test_events_for_achievements(self):
        a17 = self.machine.achievements['achievement17']
        self.start_game()

        self.assertEqual("enabled", a17.state)

        # do not post enable event again
        self.mock_event("achievement_achievement17_state_enabled")
        a17.enable()
        self.machine_run()
        self.assertEventNotCalled("achievement_achievement17_state_enabled")

        # test disable
        self.mock_event("achievement_achievement17_state_disabled")
        a17.disable()
        self.machine_run()
        self.assertEventCalled("achievement_achievement17_state_disabled")

        # but only once
        self.mock_event("achievement_achievement17_state_disabled")
        a17.disable()
        self.machine_run()
        self.assertEventNotCalled("achievement_achievement17_state_disabled")

        # test enable
        self.mock_event("achievement_achievement17_state_enabled")
        a17.enable()
        self.machine_run()
        self.assertEventCalled("achievement_achievement17_state_enabled")

        _, sub = self.machine.placeholder_manager.build_raw_template(
            "device.achievements.achievement17.selected").evaluate_and_subscribe([])
        _, sub2 = self.machine.placeholder_manager.build_raw_template(
            "device.achievements.achievement16.selected").evaluate_and_subscribe([])

        # but only once
        self.mock_event("achievement_achievement17_state_enabled")
        a17.enable()
        self.machine_run()
        self.assertEventNotCalled("achievement_achievement17_state_enabled")
        self.assertPlaceholderEvaluates("enabled", "device.achievements.achievement17.state")
        self.assertPlaceholderEvaluates(False, "device.achievements.achievement17.selected")
        self.assertFalse(sub.done())
        self.assertFalse(sub2.done())

        # test select
        self.mock_event("achievement_achievement17_state_selected")
        a17.select()
        self.machine_run()
        self.assertEventCalled("achievement_achievement17_state_selected")
        self.assertPlaceholderEvaluates("enabled", "device.achievements.achievement17.state")
        self.assertPlaceholderEvaluates(True, "device.achievements.achievement17.selected")
        self.assertTrue(sub.done())
        self.assertFalse(sub2.done())

        # but only once
        self.mock_event("achievement_achievement17_state_selected")
        a17.select()
        self.machine_run()
        self.assertEventNotCalled("achievement_achievement17_state_selected")

        # test start
        self.mock_event("achievement_achievement17_state_started")
        a17.start()
        self.machine_run()
        self.assertEventCalled("achievement_achievement17_state_started")

        # but only once
        self.mock_event("achievement_achievement17_state_started")
        a17.start()
        self.machine_run()
        self.assertEventNotCalled("achievement_achievement17_state_started")

        # test complete
        self.mock_event("achievement_achievement17_state_completed")
        a17.complete()
        self.machine_run()
        self.assertEventCalled("achievement_achievement17_state_completed")

        # but only once
        self.mock_event("achievement_achievement17_state_completed")
        a17.complete()
        self.machine_run()
        self.assertEventNotCalled("achievement_achievement17_state_completed")

    def test_rotation(self):

        a4 = self.machine.achievements['achievement4']
        a5 = self.machine.achievements['achievement5']
        a6 = self.machine.achievements['achievement6']
        g2 = self.machine.achievement_groups['group2']

        self.start_game()

        a4.enable()
        a4.select()
        a5.enable()
        a6.enable()

        self.advance_time_and_run(1)
        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertTrue(a4.selected)
        self.assertFalse(a5.selected)
        self.assertFalse(a6.selected)
        self.assertLightColor('led4', 'orange')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        # don't rotate if group is not enabled
        self.assertEqual(g2.enabled, False)
        self.post_event('group2_rotate_right', 1)
        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertTrue(a4.selected)
        self.assertFalse(a5.selected)
        self.assertFalse(a6.selected)
        self.assertLightColor('led4', 'orange')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        # enable the group and test
        self.post_event('group2_enable', 1)
        self.assertEqual(g2.enabled, True)
        self.post_event('group2_rotate_right', 1)
        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertFalse(a4.selected)
        self.assertTrue(a5.selected)
        self.assertFalse(a6.selected)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'orange')
        self.assertLightColor('led6', 'yellow')

        # rotate 2 more times to make sure
        self.post_event('group2_rotate_right', 1)
        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertFalse(a4.selected)
        self.assertFalse(a5.selected)
        self.assertTrue(a6.selected)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'orange')

        self.post_event('group2_rotate_right', 1)
        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertTrue(a4.selected)
        self.assertFalse(a5.selected)
        self.assertFalse(a6.selected)
        self.assertLightColor('led4', 'orange')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        # test rotate left
        self.post_event('group2_rotate_left', 1)
        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertFalse(a4.selected)
        self.assertFalse(a5.selected)
        self.assertTrue(a6.selected)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'orange')

        # don't rotate between disabled ones
        self.post_event('achievement4_disable', 1)
        self.assertEqual("disabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertFalse(a4.selected)
        self.assertFalse(a5.selected)
        self.assertTrue(a6.selected)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'orange')

        self.post_event('group2_rotate_right', 1)
        self.assertEqual("disabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertFalse(a4.selected)
        self.assertTrue(a5.selected)
        self.assertFalse(a6.selected)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'orange')
        self.assertLightColor('led6', 'yellow')

        # complete the event, auto_select is not enabled

        self.post_event('achievement5_start', 1)
        self.post_event('achievement5_complete', 1)

        self.assertEqual("disabled", a4.state)
        self.assertEqual("completed", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertFalse(a4.selected)
        self.assertFalse(a5.selected)
        self.assertFalse(a6.selected)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'blue')
        self.assertLightColor('led6', 'yellow')

        # rotate should not touch the complete or disabled ones

        self.post_event('group2_rotate_right', 1)
        self.assertEqual("disabled", a4.state)
        self.assertEqual("completed", a5.state)
        self.assertEqual("enabled", a6.state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'blue')
        self.assertLightColor('led6', 'yellow')
        self.assertFalse(a4.selected)
        self.assertFalse(a5.selected)
        self.assertFalse(a6.selected)

        # enable a4, select one, rotate shouldn't touch the disabled one
        self.post_event('achievement4_enable', 1)
        self.post_event('group2_random', 1)
        self.post_event('group2_rotate_right', 1)

        self.assertEqual("completed", a5.state)
        self.assertLightColor('led5', 'blue')

        if a4.selected:
            old_selected = a4
            old_enabled = a6
            self.assertLightColor('led4', 'orange')
            self.assertLightColor('led6', 'yellow')
            self.assertEqual("enabled", a6.state)
        else:
            old_selected = a6
            old_enabled = a4
            self.assertLightColor('led4', 'yellow')
            self.assertLightColor('led6', 'orange')
            self.assertEqual("enabled", a4.state)

        self.post_event('group2_rotate_right', 1)
        self.assertLightColor(old_selected.config['show_tokens']['led'], 'yellow')
        self.assertLightColor(old_enabled.config['show_tokens']['led'], 'orange')
        self.assertEqual(old_selected.state, 'enabled')
        self.assertEqual(old_enabled.state, 'enabled')
        self.assertFalse(old_selected.selected)
        self.assertTrue(old_enabled.selected)

        self.post_event('group2_rotate_right', 1)
        self.assertLightColor(old_selected.config['show_tokens']['led'], 'orange')
        self.assertLightColor(old_enabled.config['show_tokens']['led'], 'yellow')
        self.assertEqual(old_selected.state, 'enabled')
        self.assertEqual(old_enabled.state, 'enabled')
        self.assertTrue(old_selected.selected)
        self.assertFalse(old_enabled.selected)

    def test_group_completion_via_methods(self):
        a4 = self.machine.achievements['achievement4']
        a5 = self.machine.achievements['achievement5']
        a6 = self.machine.achievements['achievement6']
        g2 = self.machine.achievement_groups['group2']

        self.mock_event('group2_complete')
        self.mock_event('group2_no_more')

        self.start_game()

        _, sub = self.machine.placeholder_manager.build_raw_template(
            "device.achievement_groups.group2.enabled").evaluate_and_subscribe([])

        self.assertPlaceholderEvaluates(False, "device.achievement_groups.group2.enabled")

        # test via methods
        a4.enable()
        a5.enable()
        a6.enable()
        g2.enable()
        self.machine_run()

        self.assertPlaceholderEvaluates(True, "device.achievement_groups.group2.enabled")
        self.assertTrue(sub.done())

        self.assertEqual("enabled", a4.state)
        self.assertEqual("enabled", a5.state)
        self.assertEqual("enabled", a6.state)

        a4.select()
        self.assertTrue(a4.selected)
        self.assertEqual("enabled", a4.state)
        a4.start()
        self.assertEqual("started", a4.state)
        a4.stop()
        self.assertEqual("stopped", a4.state)
        a4.start()
        self.assertEqual("started", a4.state)
        a4.complete()
        self.assertEqual("completed", a4.state)

        a5.start()
        a5.complete()
        self.advance_time_and_run()
        self.assertEventNotCalled('group2_no_more')

        a6.start()
        self.advance_time_and_run()
        self.assertEventCalled('group2_no_more')
        self.assertEventNotCalled('group2_complete')

        a6.complete()
        self.advance_time_and_run()
        self.assertEventCalled('group2_complete')

        # re-enable & select random, should not select any

        g2.enable()
        g2.select_random_achievement()
        self.assertEqual("completed", a4.state)
        self.assertEqual("completed", a5.state)
        self.assertEqual("completed", a6.state)

    def test_group_auto_select_and_group_auto_enable(self):
        g1 = self.machine.achievement_groups['group1']

        self.start_game()

        self.assertTrue(self.machine.achievement_groups["group1"].enabled)
        selected = g1._selected_member
        self.assertTrue(selected)

        # group should auto disable
        selected.start()
        self.advance_time_and_run(.1)
        self.assertFalse(g1.enabled)

        # group should auto enable
        selected.stop()
        self.advance_time_and_run(.1)
        self.assertTrue(g1.enabled)

        _, sub = self.machine.placeholder_manager.build_raw_template(
            "device.achievement_groups.group1.selected_member").evaluate_and_subscribe([])

        selected.start()
        self.advance_time_and_run(.1)
        self.assertFalse(g1.enabled)
        selected.complete()
        self.advance_time_and_run(.1)

        # group should auto enable and select another
        self.assertTrue(g1.enabled)
        selected2 = g1._selected_member
        self.assertIsNot(selected, selected2)

        self.assertTrue(sub.done())

        selected2.start()
        self.advance_time_and_run(.1)
        selected2.complete()
        self.advance_time_and_run(.1)

        # group should auto enable and select another
        self.assertTrue(g1.enabled)
        selected3 = g1._selected_member
        self.assertIsNot(selected2, selected3)

        selected3.start()
        self.advance_time_and_run(.1)
        selected3.complete()
        self.advance_time_and_run(.1)

        # should not re-enable since all members are complete
        self.assertFalse(g1.enabled)

    def test_auto_enable_with_no_enable_events(self):
        self.start_game()

        self.assertTrue(self.machine.achievement_groups["group1"].enabled)
        self.assertFalse(self.machine.achievement_groups["group2"].enabled)

    def test_auto_select_with_no_enable_events(self):
        # a10 and 11 do not have enable events, so they should be enabled on
        # start. a12 and 13 have enable events, so they should not be enabled.
        # initial selection should pick either 10 or 11

        a10 = self.machine.achievements['achievement10']
        a11 = self.machine.achievements['achievement11']
        a12 = self.machine.achievements['achievement12']
        a13 = self.machine.achievements['achievement13']

        self.start_game()
        self.advance_time_and_run(.1)

        self.assertEqual(a10.state, 'enabled')
        self.assertEqual(a11.state, 'enabled')
        self.assertEqual(a12.state, 'disabled')
        self.assertEqual(a13.state, 'disabled')
        if a10.selected == a11.selected:
            raise AssertionError("Neither a10 nor a11 is selected")

    def _assert_selected(self, expected):
        self.assertEqual(
            expected,
            self.machine.achievements["spinTasticAward"].selected +
            self.machine.achievements["tagTeamAward"].selected +
            self.machine.achievements["doubleChanceAward"].selected +
            self.machine.achievements["extraBallAward"].selected +
            self.machine.achievements["prodigiousPopsAward"].selected,
            "Expected exactly {} achievement(s) to be selected. Found: {} {} {} {} {}".format(
                expected,
                self.machine.achievements["spinTasticAward"].selected,
                self.machine.achievements["tagTeamAward"].selected,
                self.machine.achievements["doubleChanceAward"].selected,
                self.machine.achievements["extraBallAward"].selected,
                self.machine.achievements["prodigiousPopsAward"].selected
            )
        )

    def test_auto_select_with_allow_selection_change_while_disabled(self):
        self.start_game()
        self.start_mode("auto_select")
        self._assert_selected(0)

        self.post_event("enable_group")
        self._assert_selected(1)
        self.post_event("start_event")
        self._assert_selected(1)
        self.post_event("disable_bonus")
        self._assert_selected(1)
        self.post_event("sw_pops")
        self._assert_selected(1)
        self.post_event("mode_spinTasticAward_stopped")
        self._assert_selected(1)
        self.post_event("mode_tagTeamAward_stopped")
        self._assert_selected(1)
        self.post_event("mode_doubleChanceAward_stopped")
        self._assert_selected(1)
        self.post_event("extraBallAwardIntro_complete")
        self._assert_selected(1)
        self.post_event("mode_prodigiousPopsAward_stopped")
        self.advance_time_and_run(.1)
        self._assert_selected(1)
