"""Test achievements."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestAchievement(MpfFakeGameTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/achievement/'

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

        # start disabled
        self.assertEqual("achievement1_disabled", achievement._show.name)
        self.assertEqual("disabled", achievement._state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(0, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(0, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_stopped'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        # should not start
        self.post_event("achievement1_start")
        self.assertEqual("disabled", achievement._state)

        # enable
        self.post_event("achievement1_enable")
        self.assertEqual("enabled", achievement._state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(0, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertEqual("achievement1_enabled", achievement._show.name)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_enabled']['restore'])

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement._state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertEqual("achievement1_started", achievement._show.name)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_started']['restore'])

        self.drain_ball()

        self.assertPlayerNumber(2)
        self.assertBallNumber(1)
        self.assertEqual("achievement1_disabled", achievement._show.name)
        self.assertEqual("disabled", achievement._state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        self.post_event("achievement1_enable")
        self.assertEqual("achievement1_enabled", achievement._show.name)
        self.assertEqual("enabled", achievement._state)

        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.assertEqual("achievement1_started", achievement._show.name)
        self.assertEqual("started", achievement._state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_started']['restore'])

        self.post_event("achievement1_complete")
        self.assertEqual("achievement1_completed", achievement._show.name)
        self.assertEqual("completed", achievement._state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_completed']['restore'])

        self.post_event("achievement1_enable")
        self.post_event("achievement1_disable")
        self.post_event("achievement1_stop")
        self.assertEqual("completed", achievement._state)

        self.drain_ball()
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        self.assertEqual("achievement1_enabled", achievement._show.name)
        self.assertEqual("enabled", achievement._state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_enabled']['restore'])

        self.post_event("achievement1_disable")
        self.assertEqual("disabled", achievement._state)

        self.post_event("achievement1_enable")
        self.assertEqual("enabled", achievement._state)

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement._state)

        self.post_event("achievement1_stop")
        self.assertEqual("stopped", achievement._state)
        self.assertEqual("achievement1_stopped", achievement._show.name)

        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.assertEqual("achievement1_completed", achievement._show.name)
        self.assertEqual("completed", achievement._state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_completed']['restore'])

        self.post_event("achievement1_reset")
        self.assertEqual("achievement1_disabled", achievement._show.name)
        self.assertEqual("disabled", achievement._state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        self.drain_ball()
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        self.assertEqual("stopped", achievement._state)
        self.assertEqual("achievement1_stopped", achievement._show.name)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_stopped']['restore'])

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement._state)

        self.drain_ball()
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
        self.assertEqual("enabled", achievement._state)
        self.assertLightColor('led1', 'yellow')

        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        self.assertEqual(None, achievement._show)
        self.assertEqual("disabled", achievement._state)
        self.assertLightColor('led1', 'off')

        self.post_event("achievement2_enable", 2)
        self.assertEqual("enabled", achievement._state)
        self.assertLightColor('led1', 'yellow')

        self.assertEqual(0, self._events['test_event'])
        self.assertEqual(0, self._events['test_event2'])

        self.post_event("achievement2_start", 2)
        self.assertEqual("achievement2_started", achievement._show.name)
        self.assertEqual("started", achievement._state)
        self.assertLightColor('led1', 'green')

        self.assertEqual(1, self._events['test_event'])
        self.assertEqual(1, self._events['test_event2'])
        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.assertEqual("stopped", achievement._state)
        self.assertEqual(None, achievement._show)
        self.assertLightColor('led1', 'off')  # no show when stopped

        # restart after stop is False
        self.post_event("achievement2_start", 2)
        self.assertEqual("stopped", achievement._state)
        self.assertLightColor('led1', 'off')

    def test_group_select(self):

        a4 = self.machine.achievements['achievement4']
        a5 = self.machine.achievements['achievement5']
        a6 = self.machine.achievements['achievement6']
        g2 = self.machine.achievement_groups.group2

        self.start_game()

        self.assertFalse(g2.enabled)
        self.assertEqual("disabled", a4._state)
        self.assertEqual("disabled", a5._state)
        self.assertEqual("disabled", a6._state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'off')
        self.assertLightColor('led6', 'off')

        # achievements are disabled, should select none

        self.post_event('group2_random', 2)

        enabled_achievements = [x for x in (a4, a5, a6) if x._state == 'enabled']
        self.assertEqual(len(enabled_achievements), 0)

        # enable the achievements and try again, but group is disabled

        a4.enable()
        a5.enable()
        a6.enable()

        self.assertEqual("enabled", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("enabled", a6._state)
        self.advance_time_and_run(1)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        self.post_event('group2_random', 2)

        selected_achievements = [x for x in (a4, a5, a6) if x._state == 'selected']
        self.assertEqual(len(selected_achievements), 0)

        # now enable the group and it should work

        self.post_event('group2_enable', 2)
        self.assertTrue(g2._enabled)
        self.assertLightColors('led2', ['red', 'blue'], 1, .09)  # group led

        self.post_event('group2_random', 2)
        selected_achievements = [x for x in (a4, a5, a6) if x._state == 'selected']
        self.assertEqual(len(selected_achievements), 1)

        # group enabled, but individual members disabled, should not work

        a4.disable()
        a5.disable()
        a6.disable()
        self.advance_time_and_run(1)

        self.assertEqual("disabled", a4._state)
        self.assertEqual("disabled", a5._state)
        self.assertEqual("disabled", a6._state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'off')
        self.assertLightColor('led6', 'off')

        self.post_event('group2_random', 2)
        selected_achievements = [x for x in (a4, a5, a6) if x._state == 'selected']
        self.assertEqual(len(selected_achievements), 0)

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
        self.assertEqual("selected", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'orange')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        # don't rotate if group is not enabled
        self.assertEqual(g2.enabled, False)
        self.post_event('group2_rotate_right', 1)
        self.assertEqual("selected", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'orange')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        # enable the group and test
        self.post_event('group2_enable', 1)
        self.assertEqual(g2.enabled, True)
        self.post_event('group2_rotate_right', 1)
        self.assertEqual("enabled", a4._state)
        self.assertEqual("selected", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'orange')
        self.assertLightColor('led6', 'yellow')

        # rotate 2 more times to make sure
        self.post_event('group2_rotate_right', 1)
        self.assertEqual("enabled", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("selected", a6._state)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'orange')

        self.post_event('group2_rotate_right', 1)
        self.assertEqual("selected", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'orange')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'yellow')

        # test rotate left
        self.post_event('group2_rotate_left', 1)
        self.assertEqual("enabled", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("selected", a6._state)
        self.assertLightColor('led4', 'yellow')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'orange')

        # don't rotate between disabled ones
        self.post_event('achievement4_disable', 1)
        self.assertEqual("disabled", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("selected", a6._state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'yellow')
        self.assertLightColor('led6', 'orange')

        self.post_event('group2_rotate_right', 1)
        self.assertEqual("disabled", a4._state)
        self.assertEqual("selected", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'orange')
        self.assertLightColor('led6', 'yellow')

        # complete the event, auto_select is not enabled

        self.post_event('achievement5_start', 1)
        self.post_event('achievement5_complete', 1)

        self.assertEqual("disabled", a4._state)
        self.assertEqual("completed", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'blue')
        self.assertLightColor('led6', 'yellow')

        # rotate should not touch the complete or disabled ones

        self.post_event('group2_rotate_right', 1)
        self.assertEqual("disabled", a4._state)
        self.assertEqual("completed", a5._state)
        self.assertEqual("enabled", a6._state)
        self.assertLightColor('led4', 'off')
        self.assertLightColor('led5', 'blue')
        self.assertLightColor('led6', 'yellow')

        # enable a4, select one, rotate shouldn't touch the disabled one

        self.post_event('achievement4_enable', 1)
        self.post_event('group2_random', 1)
        self.post_event('group2_rotate_right', 1)

        self.assertEqual("completed", a5._state)
        self.assertLightColor('led5', 'blue')

        if a4.state == 'selected':
            old_selected = a4
            old_enabled = a6
            self.assertLightColor('led4', 'orange')
            self.assertLightColor('led6', 'yellow')
            self.assertEqual("enabled", a6._state)
        else:
            old_selected = a6
            old_enabled = a4
            self.assertLightColor('led4', 'yellow')
            self.assertLightColor('led6', 'orange')
            self.assertEqual("enabled", a4._state)

        self.post_event('group2_rotate_right', 1)
        self.assertLightColor(old_selected.config['show_tokens']['led'], 'yellow')
        self.assertLightColor(old_enabled.config['show_tokens']['led'], 'orange')
        self.assertEqual(old_selected.state, 'enabled')
        self.assertEqual(old_enabled.state, 'selected')

        self.post_event('group2_rotate_right', 1)
        self.assertLightColor(old_selected.config['show_tokens']['led'], 'orange')
        self.assertLightColor(old_enabled.config['show_tokens']['led'], 'yellow')
        self.assertEqual(old_selected.state, 'selected')
        self.assertEqual(old_enabled.state, 'enabled')

    def test_group_completion_via_methods(self):
        a4 = self.machine.achievements['achievement4']
        a5 = self.machine.achievements['achievement5']
        a6 = self.machine.achievements['achievement6']
        g2 = self.machine.achievement_groups['group2']

        self.mock_event('group2_complete')
        self.mock_event('group2_no_more')

        self.start_game()

        # test via methods
        a4.enable()
        a5.enable()
        a6.enable()
        g2.enable()

        self.assertEqual("enabled", a4._state)
        self.assertEqual("enabled", a5._state)
        self.assertEqual("enabled", a6._state)

        a4.select()
        self.assertEqual("selected", a4._state)
        a4.start()
        self.assertEqual("started", a4._state)
        a4.stop()
        self.assertEqual("stopped", a4._state)
        a4.start()
        self.assertEqual("started", a4._state)
        a4.complete()
        self.assertEqual("completed", a4._state)

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
        self.assertEqual("completed", a4._state)
        self.assertEqual("completed", a5._state)
        self.assertEqual("completed", a6._state)

    def test_group_auto_select_and_group_auto_enable(self):
        a7 = self.machine.achievements['achievement7']
        a8 = self.machine.achievements['achievement8']
        a9 = self.machine.achievements['achievement9']
        g1 = self.machine.achievement_groups['group1']

        self.start_game()

        self.assertTrue(self.machine.achievement_groups.group1.enabled)
        selected = g1._selected_member
        self.assertTrue(selected)

        # group should auto disable
        selected.start()
        self.assertFalse(g1.enabled)

        # group should auto enable
        selected.stop()
        self.assertTrue(g1.enabled)

        selected.start()
        self.assertFalse(g1.enabled)
        selected.complete()

        # group should auto enable and select another
        self.assertTrue(g1.enabled)
        selected2 = g1._selected_member
        self.assertIsNot(selected, selected2)

        selected2.start()
        selected2.complete()

        # group should auto enable and select another
        self.assertTrue(g1.enabled)
        selected3 = g1._selected_member
        self.assertIsNot(selected2, selected3)

        selected3.start()
        selected3.complete()

        # should not re-enable since all members are complete
        self.assertFalse(g1.enabled)

    def test_auto_enable_with_no_enable_events(self):
        self.start_game()

        self.assertTrue(self.machine.achievement_groups.group1.enabled)
        self.assertFalse(self.machine.achievement_groups.group2.enabled)

    def test_auto_select_with_no_enable_events(self):
        # a10 and 11 do not have enable events, so they should be enabled on
        # start. a12 and 13 have enable events, so they should not be enabled.
        # initial selection should pick either 10 or 11

        a10 = self.machine.achievements['achievement10']
        a11 = self.machine.achievements['achievement11']
        a12 = self.machine.achievements['achievement12']
        a13 = self.machine.achievements['achievement13']
        g3 = self.machine.achievement_groups['group3']

        self.start_game()

        if a10.state == 'selected':
            self.assertEqual(a11.state, 'enabled')
        elif a11.state == 'selected':
            self.assertEqual(a10.state, 'enabled')
        else:
            raise AssertionError("Neither a10 nor a11 is selected")

        self.assertEqual(a12.state, 'disabled')
        self.assertEqual(a13.state, 'disabled')

