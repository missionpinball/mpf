"""Test achievements."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfShowTestCase import MpfShowTestCase


class TestAchievement(MpfFakeGameTestCase, MpfShowTestCase):
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

        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_completed")

        self.start_two_player_game()
        self.assertIn(self.machine.modes['base'], self.machine.mode_controller.active_modes)

        achievement = self.machine.achievements['achievement1']

        # start disabled
        self.assertShowRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_completed")
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
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_completed")
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_enabled']['restore'])

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement._state)
        self.assertEqual(1, self._events['achievement_achievement1_state_disabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_enabled'])
        self.assertEqual(1, self._events['achievement_achievement1_state_started'])
        self.assertEqual(0, self._events['achievement_achievement1_state_completed'])
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_completed")
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_started']['restore'])

        self.drain_ball()

        self.assertPlayerNumber(2)
        self.assertBallNumber(1)
        self.assertShowRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_completed")
        self.assertEqual("disabled", achievement._state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        self.post_event("achievement1_enable")
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_completed")
        self.assertEqual("enabled", achievement._state)

        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_completed")
        self.assertEqual("started", achievement._state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_started']['restore'])

        self.post_event("achievement1_complete")
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowRunning("achievement1_completed")
        self.assertEqual("completed", achievement._state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_completed']['restore'])

        self.post_event("achievement1_enable")
        self.post_event("achievement1_disable")
        self.post_event("achievement1_stop")
        self.assertEqual("completed", achievement._state)

        self.drain_ball()
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_completed")
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
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_completed")

        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowRunning("achievement1_completed")
        self.assertEqual("completed", achievement._state)
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_completed']['restore'])

        self.post_event("achievement1_reset")
        self.assertShowRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_completed")
        self.assertEqual("disabled", achievement._state)
        self.assertFalse(self._last_event_kwargs['achievement_achievement1_state_disabled']['restore'])

        self.drain_ball()
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        self.assertEqual("stopped", achievement._state)
        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_completed")
        self.assertTrue(self._last_event_kwargs['achievement_achievement1_state_stopped']['restore'])

        self.post_event("achievement1_start")
        self.assertEqual("started", achievement._state)

        self.drain_ball()
        self.assertGameIsNotRunning()

        self.assertShowNotRunning("achievement1_disabled")
        self.assertShowNotRunning("achievement1_enabled")
        self.assertShowNotRunning("achievement1_started")
        self.assertShowNotRunning("achievement1_stopped")
        self.assertShowNotRunning("achievement1_completed")

    def test_one_player_no_restart(self):
        self.mock_event("test_event")
        self.mock_event("test_event2")
        self.assertShowNotRunning("achievement2_enabled")
        self.assertShowNotRunning("achievement2_started")
        self.assertShowNotRunning("achievement2_completed")

        self.start_game()

        achievement = self.machine.achievements['achievement2']

        # start enabled
        self.assertShowRunning("achievement2_enabled")
        self.assertShowNotRunning("achievement2_started")
        self.assertShowNotRunning("achievement2_completed")
        self.assertEqual("enabled", achievement._state)

        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        self.assertShowNotRunning("achievement2_enabled")
        self.assertShowNotRunning("achievement2_started")
        self.assertShowNotRunning("achievement2_completed")
        self.assertEqual("disabled", achievement._state)

        self.post_event("achievement2_enable")
        self.assertEqual("enabled", achievement._state)

        self.assertEqual(0, self._events['test_event'])
        self.assertEqual(0, self._events['test_event2'])

        self.post_event("achievement2_start")
        self.assertShowNotRunning("achievement2_enabled")
        self.assertShowRunning("achievement2_started")
        self.assertShowNotRunning("achievement2_completed")
        self.assertEqual("started", achievement._state)

        self.assertEqual(1, self._events['test_event'])
        self.assertEqual(1, self._events['test_event2'])
        self.drain_ball()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.assertEqual("stopped", achievement._state)
        self.assertShowNotRunning("achievement2_enabled")
        self.assertShowNotRunning("achievement2_started")
        self.assertShowNotRunning("achievement2_completed")

        self.post_event("achievement2_start")
        self.assertEqual("stopped", achievement._state)
