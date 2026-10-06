from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestStateMachine(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/state_machine/'

    def test_state_machine(self):
        placeholder_str = "device.state_machines.my_state.state"
        placeholder = self.machine.placeholder_manager.build_raw_template(placeholder_str)
        placeholder_value, placeholder_future = placeholder.evaluate_and_subscribe([])
        self.assertPlaceholderEvaluates("start", placeholder_str)
        self.assertEqual("start", self.machine.state_machines["my_state"].state)

        self.mock_event("step1_start")
        self.mock_event("step1_stop")
        self.mock_event("going_to_step2")
        self.post_event("state_machine_proceed")
        self.assertPlaceholderEvaluates("step1", placeholder_str)
        self.assertEqual("step1", self.machine.state_machines["my_state"].state)
        self.assertTrue(placeholder_future.done())
        self.assertEqual("on", self.machine.state_machines["my_state"]._show.name)
        self.assertEventCalled("step1_start")
        self.mock_event("step1_start")
        self.assertEventNotCalled("step1_stop")
        self.assertEventNotCalled("going_to_step2")
        self.post_event("state_machine_proceed")
        self.assertEqual("step1", self.machine.state_machines["my_state"].state)
        self.assertEventNotCalled("step1_start")
        self.assertEventNotCalled("step1_stop")
        self.assertEventNotCalled("going_to_step2")

        self.post_event("state_machine_proceed2")
        self.assertEqual("step2", self.machine.state_machines["my_state"].state)
        self.assertEqual(None, self.machine.state_machines["my_state"]._show)
        self.assertEventNotCalled("step1_start")
        self.assertEventCalled("step1_stop")
        self.assertEventCalled("going_to_step2")
        self.post_event("state_machine_proceed2")
        self.assertEqual("step2", self.machine.state_machines["my_state"].state)

        self.post_event("state_machine_proceed3")
        self.assertEqual("start", self.machine.state_machines["my_state"].state)

        self.post_event("state_machine_proceed")
        self.assertEqual("step1", self.machine.state_machines["my_state"].state)

        self.post_event("state_machine_reset")
        self.assertEqual("start", self.machine.state_machines["my_state"].state)

    def test_state_machines_in_modes(self):
        self.mock_event("non_game_mode_state_machine_done")
        self.mock_event("game_mode_state_machine_done")

        self.post_event("non_game_mode_state_machine_proceed")
        self.assertEventCalled("non_game_mode_state_machine_done")
        self.assertEventNotCalled("game_mode_state_machine_done")
        self.mock_event("non_game_mode_state_machine_done")

        self.post_event("game_mode_state_machine_proceed")
        self.assertEventNotCalled("non_game_mode_state_machine_done")
        self.assertEventNotCalled("game_mode_state_machine_done")

        placeholder = self.machine.placeholder_manager.build_string_template(
            "device.state_machines.game_mode_state_machine.state", "")
        value, future = placeholder.evaluate_and_subscribe({})
        self.assertEqual(value, "")

        self.start_game()

        self.assertTrue(future.done())
        value, future = placeholder.evaluate_and_subscribe({})
        self.assertEqual(value, "start")
        self.assertFalse(future.done())

        self.post_event("game_mode_state_machine_proceed")
        self.assertEventNotCalled("non_game_mode_state_machine_done")
        self.assertEventCalled("game_mode_state_machine_done")
        self.assertTrue(future.done())
        value, future = placeholder.evaluate_and_subscribe({})
        self.assertEqual(value, "done")
        self.assertFalse(future.done())

        self.stop_game()
        self.assertTrue(future.done())
        value, future = placeholder.evaluate_and_subscribe({})
        self.assertEqual(value, "")
        self.assertFalse(future.done())

    def test_starting_state(self):
        self.assertEqual("foo", self.machine.state_machines["second_state"].state)
        self.post_event("state_machine_outoforder")
        self.assertEqual("bar", self.machine.state_machines["second_state"].state)

    def test_repost_start_events_on_restore_boolean(self):
        """Verifies root boolean forces standard start events to re-fire on restore."""
        self.mock_event("repost_machine_done")
        self.start_game()

        sm = self.machine.state_machines["persisted_repost_machine"]
        self.assertEqual("start", sm.state)

        # Advance to done and verify the start event fired
        self.post_event("repost_machine_proceed")
        self.assertEqual("done", sm.state)
        self.assertEventCalled("repost_machine_done")

        self.mock_event("repost_machine_done")
        self.assertEventNotCalled("repost_machine_done")

        # Cycle the mode
        self.machine.modes["game_mode"].stop()
        self.advance_time_and_run(0.1)
        self.machine.modes["game_mode"].start()
        self.advance_time_and_run(0.1)

        self.assertEqual("done", sm.state)
        self.assertEventCalled("repost_machine_done")

    def test_explicit_events_when_restored(self):
        """Verifies explicit restore hooks override start events on restore."""
        self.mock_event("explicit_machine_done")
        self.mock_event("explicit_machine_restored")
        self.start_game()

        sm = self.machine.state_machines["persisted_explicit_machine"]
        self.assertEqual("start", sm.state)

        # Advance to done
        self.post_event("explicit_machine_proceed")
        self.assertEqual("done", sm.state)
        self.assertEventCalled("explicit_machine_done")
        self.assertEventNotCalled("explicit_machine_restored")

        self.mock_event("explicit_machine_done")
        self.mock_event("explicit_machine_restored")
        self.assertEventNotCalled("explicit_machine_done")
        self.assertEventNotCalled("explicit_machine_restored")

        # Cycle the mode
        self.machine.modes["game_mode"].stop()
        self.advance_time_and_run(0.1)
        self.machine.modes["game_mode"].start()
        self.advance_time_and_run(0.1)

        self.assertEqual("done", sm.state)
        self.assertEventNotCalled("explicit_machine_done")
        self.assertEventCalled("explicit_machine_restored")

    def test_repost_initial_state_on_restore(self):
        """Proves initial state event behavior on restoration loops."""
        self.mock_event("repost_machine_start_fired")
        self.mock_event("repost_machine_start_restored")

        # expect standard start event
        self.start_game()
        sm = self.machine.state_machines["persisted_repost_machine"]
        self.assertEqual("start", sm.state)
        self.assertEventCalled("repost_machine_start_fired")
        self.assertEventNotCalled("repost_machine_start_restored")

        self.mock_event("repost_machine_start_fired")
        self.mock_event("repost_machine_start_restored")

        # stop while still in initial state
        self.machine.modes["game_mode"].stop()
        self.advance_time_and_run(0.1)
        self.assertIsNone(sm.state)

        # restart mode
        self.machine.modes["game_mode"].start()
        self.advance_time_and_run(0.1)
        self.assertEqual("start", sm.state)

        self.assertEventCalled("repost_machine_start_restored")
        # events_when_restored wins over when started if both set
        self.assertEventNotCalled("repost_machine_start_fired")
