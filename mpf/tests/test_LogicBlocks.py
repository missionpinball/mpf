"""Test logic blocks."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import test_config_directory


class TestLogicBlocks(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/logic_blocks/'

    def test_mode_selection_with_counters(self):
        self.mock_event("qualify_start_mode1")
        self.mock_event("qualify_start_mode2")
        self.start_game()
        self.start_mode("mode3")
        # advance both counters to 2/3
        self.post_event("qualify1_count")
        self.post_event("qualify1_count")
        self.post_event("qualify2_count")
        self.post_event("qualify2_count")

        # post the final even for both of them
        self.machine.switch_controller.process_switch("s_qualify1", 1, True)
        self.machine.switch_controller.process_switch("s_qualify2", 1, True)
        self.advance_time_and_run()
        self.assertEventCalled("qualify_start_mode1")
        self.assertEventNotCalled("qualify_start_mode2")

    @test_config_directory("tests/machine_files/counters/")
    def test_subscription_on_counter_values(self):
        self.start_game()
        self.start_mode("mode1")
        self.assertLightColor("l_chest_matrix_green_2", "black")
        self.assertLightColor("l_chest_matrix_green_3", "black")
        self.assertLightColor("l_chest_matrix_green_4", "black")
        self.assertLightColor("l_chest_matrix_green_5", "black")
        self.post_event("count_up")
        self.advance_time_and_run(.1)
        self.assertLightColor("l_chest_matrix_green_2", "black")
        self.assertLightColor("l_chest_matrix_green_3", "black")
        self.assertLightColor("l_chest_matrix_green_4", "black")
        self.assertLightColor("l_chest_matrix_green_5", "green")
        self.post_event("count_up")
        self.advance_time_and_run(.1)
        self.assertLightColor("l_chest_matrix_green_2", "black")
        self.assertLightColor("l_chest_matrix_green_3", "black")
        self.assertLightColor("l_chest_matrix_green_4", "green")
        self.assertLightColor("l_chest_matrix_green_5", "green")
        self.post_event("count_up")
        self.advance_time_and_run(.1)
        self.assertLightColor("l_chest_matrix_green_2", "black")
        self.assertLightColor("l_chest_matrix_green_3", "green")
        self.assertLightColor("l_chest_matrix_green_4", "green")
        self.assertLightColor("l_chest_matrix_green_5", "green")
        self.post_event("count_up")
        self.advance_time_and_run(.1)
        self.assertLightColor("l_chest_matrix_green_2", "green")
        self.assertLightColor("l_chest_matrix_green_3", "green")
        self.assertLightColor("l_chest_matrix_green_4", "green")
        self.assertLightColor("l_chest_matrix_green_5", "green")

        self.drain_all_balls()
        self.advance_time_and_run()
        self.start_mode("mode1")

        self.assertLightColor("l_chest_matrix_green_2", "black")
        self.assertLightColor("l_chest_matrix_green_3", "black")
        self.assertLightColor("l_chest_matrix_green_4", "black")
        self.assertLightColor("l_chest_matrix_green_5", "black")

    def test_counter_with_lights(self):
        self.start_game()
        self.post_event("start_mode2")
        self.advance_time_and_run()

        self.assertLightColor("led1", "white")
        self.assertLightColor("led2", "black")
        self.assertLightColor("led3", "black")

        # nothing happens because it is disabled
        self.post_event("counter_with_lights_count")
        self.advance_time_and_run()
        self.assertLightColor("led1", "white")
        self.assertLightColor("led2", "black")
        self.assertLightColor("led3", "black")

        # advance
        self.post_event("counter_with_lights_enable")
        self.post_event("counter_with_lights_count")
        self.advance_time_and_run()
        self.assertLightColor("led1", "black")
        self.assertLightColor("led2", "white")
        self.assertLightColor("led3", "black")

        # stop mode
        self.post_event("stop_mode2")
        self.advance_time_and_run()

        # all off
        self.assertLightColor("led1", "black")
        self.assertLightColor("led2", "black")
        self.assertLightColor("led3", "black")

        # restart mode. should restore state
        self.post_event("start_mode2")
        self.advance_time_and_run()
        self.assertLightColor("led1", "black")
        self.assertLightColor("led2", "white")
        self.assertLightColor("led3", "black")

        # and complete
        self.post_event("counter_with_lights_count")
        self.advance_time_and_run()
        self.assertLightColor("led1", "black")
        self.assertLightColor("led2", "black")
        self.assertLightColor("led3", "white")

    def test_accrual_random_advance(self):
        self.start_game()
        self.mock_event("accrual1_complete1")

        # should do nothing
        self.post_event("accrual1_random_advance")
        self.assertEqual([False, False, False], self.machine.accruals["accrual1"].value)

        # enable accrual
        self.post_event("accrual1_enable")

        # complete one step
        self.post_event("accrual1_step1a")
        self.assertEqual([True, False, False], self.machine.accruals["accrual1"].value)

        # should advance one of the remaining steps
        self.post_event("accrual1_random_advance")

        # exactly two steps should be hit
        self.assertEqual(2, sum(self.machine.accruals["accrual1"].value))
        self.assertEventNotCalled("accrual1_complete1")

        # should complete the accrual
        self.post_event("accrual1_random_advance")

        self.assertEventCalled("accrual1_complete1")

    def test_accruals_simple(self):
        self.start_game()
        self.mock_event("accrual1_complete1")
        self.mock_event("accrual1_hit")
        self.mock_event("accrual1_complete2")

        # accrual should not yet work
        self.post_event("accrual1_step1a")
        self.post_event("accrual1_step2b")
        self.post_event("accrual1_step3c")

        self.assertEqual(0, self._events["accrual1_complete1"])
        self.assertEqual(0, self._events["accrual1_complete2"])

        # enable accrual
        self.post_event("accrual1_enable")

        # step2
        self.post_event("accrual1_step2a")
        self.assertEqual(0, self._events["accrual1_complete1"])
        self.assertEqual(1, self._events["accrual1_hit"])

        # step1
        self.post_event("accrual1_step1c")
        self.post_event("accrual1_step1b")
        self.assertEqual(0, self._events["accrual1_complete1"])
        self.assertEqual(2, self._events["accrual1_hit"])

        # step 3
        self.post_event("accrual1_step3c")

        # accrual should fire
        self.assertEqual(1, self._events["accrual1_complete1"])
        self.assertEqual(1, self._events["accrual1_complete2"])

        # should not work again
        self.post_event("accrual1_step1a")
        self.post_event("accrual1_step2a")
        self.post_event("accrual1_step3a")
        self.assertEqual(1, self._events["accrual1_complete1"])
        self.assertEqual(1, self._events["accrual1_complete2"])

        # reset but do not enable yet
        self.post_event("accrual1_reset")

        # nothing should happen
        self.post_event("accrual1_step1a")
        self.post_event("accrual1_step2a")
        self.post_event("accrual1_step3a")
        self.assertEqual(1, self._events["accrual1_complete1"])
        self.assertEqual(1, self._events["accrual1_complete2"])

        # enable for one step
        self.post_event("accrual1_enable")
        self.post_event("accrual1_step1a")

        # disable for next
        self.post_event("accrual1_disable")
        self.post_event("accrual1_step2a")

        # enable for third step
        self.post_event("accrual1_enable")
        self.post_event("accrual1_step3a")

        # should not complete yet
        self.assertEqual(1, self._events["accrual1_complete1"])
        self.assertEqual(1, self._events["accrual1_complete2"])

        self.post_event("accrual1_step2a")

        # but now
        self.assertEqual(2, self._events["accrual1_complete1"])
        self.assertEqual(2, self._events["accrual1_complete2"])

    def test_counter_simple_down(self):
        self.start_game()
        self.mock_event("logicblock_counter1_complete")
        self.mock_event("logicblock_counter1_hit")

        self.post_event("counter1_enable")
        for i in range(4):
            self.post_event("counter1_count")
            self.assertEqual(0, self._events["logicblock_counter1_complete"])

        # nothing should happen when disabled
        self.post_event("counter1_disable")
        for i in range(10):
            self.post_event("counter1_count")
            self.assertEqual(0, self._events["logicblock_counter1_complete"])
        self.post_event("counter1_enable")

        self.post_event("counter1_count")
        self.assertEqual(1, self._events["logicblock_counter1_complete"])
        self.assertEqual(5, self._events["logicblock_counter1_hit"])

        # it should disable
        self.post_event("counter1_count")
        self.assertEqual(1, self._events["logicblock_counter1_complete"])
        self.assertEqual(5, self._events["logicblock_counter1_hit"])

        self.post_event("counter1_restart")

        for i in range(4):
            self.post_event("counter1_count")

        # 4 more hits but not completed
        self.assertEqual(1, self._events["logicblock_counter1_complete"])
        self.assertEqual(9, self._events["logicblock_counter1_hit"])

        # reset
        self.post_event("counter1_reset")
        for i in range(4):
            self.post_event("counter1_count")

        # another 4 hits still not complete
        self.assertEqual(1, self._events["logicblock_counter1_complete"])
        self.assertEqual(13, self._events["logicblock_counter1_hit"])

        # and complete again
        self.post_event("counter1_count")
        self.assertEqual(2, self._events["logicblock_counter1_complete"])
        self.assertEqual(14, self._events["logicblock_counter1_hit"])

    def test_sequence_simple(self):
        self.start_game()
        self.mock_event("sequence1_complete")
        self.mock_event("logicblock_sequence1_hit")

        self.post_event("sequence1_enable")

        # wrong order
        self.post_event("sequence1_step3a")
        self.post_event("sequence1_step2a")
        self.post_event("sequence1_step1b")
        self.assertEqual(0, self._events["sequence1_complete"])
        self.assertEqual(1, self._events["logicblock_sequence1_hit"])

        # still not
        self.post_event("sequence1_step3b")
        self.post_event("sequence1_step1a")
        self.assertEqual(0, self._events["sequence1_complete"])
        self.assertEqual(1, self._events["logicblock_sequence1_hit"])

        # only 1 so far. now step2
        self.post_event("sequence1_step2a")
        self.assertEqual(0, self._events["sequence1_complete"])
        self.assertEqual(2, self._events["logicblock_sequence1_hit"])

        # and step 3
        self.post_event("sequence1_step3b")
        self.assertEqual(1, self._events["sequence1_complete"])
        self.assertEqual(3, self._events["logicblock_sequence1_hit"])

        # should be disabled
        self.post_event("sequence1_step1a")
        self.post_event("sequence1_step2a")
        self.post_event("sequence1_step3a")
        self.assertEqual(1, self._events["sequence1_complete"])

        # enable and reset
        self.post_event("sequence1_enable")
        self.post_event("sequence1_reset")

        # reset inbetween
        self.post_event("sequence1_step1a")
        self.post_event("sequence1_step2a")
        self.post_event("sequence1_reset")
        self.post_event("sequence1_step3a")

        # nothing
        self.assertEqual(1, self._events["sequence1_complete"])

        # again
        self.post_event("sequence1_step1a")
        self.assertEqual(1, self._events["sequence1_complete"])
        self.post_event("sequence1_step2a")
        self.assertEqual(1, self._events["sequence1_complete"])
        self.post_event("sequence1_step3a")
        self.assertEqual(2, self._events["sequence1_complete"])

    def test_counter_in_mode(self):
        self.start_game()
        self.mock_event("counter2_complete")
        self.mock_event("counter2_hit")

        for i in range(10):
            self.post_event("counter2_count")
            self.assertEqual(0, self._events["counter2_complete"])

        self.post_event("start_mode1")
        self.assertTrue("mode1" in self.machine.modes)

        for i in range(2):
            self.post_event("counter2_count")
            self.assertEqual(i + 1, self._events["counter2_hit"])
            self.assertEqual(0, self._events["counter2_complete"])
            self.assertEventCalledWith("counter2_hit", count=i + 1, remaining=2 - i, hits=i+1)

        self.post_event("counter2_count")
        self.assertEqual(1, self._events["counter2_complete"])
        self.assertEventCalledWith("counter2_hit", count=3, hits=3, remaining=0)

        # should run again
        for i in range(2):
            self.post_event("counter2_count")
            self.assertEqual(i + 4, self._events["counter2_hit"])
            self.assertEqual(1, self._events["counter2_complete"])

        self.post_event("counter2_count")
        self.assertEqual(2, self._events["counter2_complete"])

        # stop mode
        self.post_event("stop_mode1")

        # nothing should happen any more
        for i in range(10):
            self.post_event("counter2_count")
            self.assertEqual(2, self._events["counter2_complete"])
            self.assertEqual(6, self._events["counter2_hit"])

    def test_counter_control_events(self):
        '''
        Tests the add, subtract, and set_value control events
        for the Counter class.
        '''
        def reset_event_mocks():
            # Reset mocks
            self.mock_event("counter6_complete")
            self.mock_event("counter6_hit")
            self.mock_event("counter7_complete")
            self.mock_event("counter7_hit")
        self.start_game()
        reset_event_mocks()
        # Start mode with control events and counter6
        self.post_event("start_mode4")
        self.assertTrue("mode4" in self.machine.modes)

        # Adds zero to the counter 10 times, counter should not reach completion
        for i in range(10):
            self.post_event("increase_counter6_0")
            self.assertEqual(0, self._events["counter6_complete"])
        # Counts the counter once, and then adds 3 to it 3 times,
        # The last adding of three should cause the counter to complete once
        for i in range(0, 2):
            self.post_event("increase_counter6_3")
            self.assertEqual(0, self._events["counter6_complete"])
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=7, hits=7, remaining=3)
        self.post_event("increase_counter6_3")
        self.assertEqual(1, self._events["counter6_complete"])

        # Test the adding of five to the counter
        reset_event_mocks()
        self.post_event("increase_counter6_5")
        self.assertEqual(0, self._events["counter6_complete"])
        self.post_event("increase_counter6_5")
        self.assertEqual(1, self._events["counter6_complete"])

        # Test subtraction
        reset_event_mocks()
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=1, hits=1, remaining=9)
        self.post_event("reduce_counter6_5")
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=-3, hits=-3, remaining=13)
        self.post_event("reduce_counter6_3")
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=-5, hits=-5, remaining=15)
        self.post_event("reduce_counter6_0")
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=-4, hits=-4, remaining=14)

        # Test Setting the Counter to a value
        reset_event_mocks()
        # Make sure that the counter holds a nonzero value
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=-3, hits=-3, remaining=13)
        self.post_event("set_counter6_0")
        self.post_event("counter6_count")
        self.assertEventCalledWith("counter6_hit", count=1, hits=1, remaining=9)
        # Set the counter to a value above the completion value
        self.assertEqual(0, self._events["counter6_complete"])
        self.post_event("set_counter6_25")
        self.assertEqual(1, self._events["counter6_complete"])

        # Test using counter with direction down
        # Test increasing and reducing
        reset_event_mocks()
        self.post_event("counter7_count")
        self.assertEventCalledWith("counter7_hit", count=4, hits=1, remaining=4)
        self.post_event("increase_counter7_5")
        self.post_event("counter7_count")
        self.assertEventCalledWith("counter7_hit", count=8, hits=-3, remaining=8)
        self.post_event("reduce_counter7_5")
        self.post_event("counter7_count")
        self.assertEventCalledWith("counter7_hit", count=2, hits=3, remaining=2)
        self.assertEqual(0, self._events["counter7_complete"])
        self.post_event("reduce_counter7_3")
        self.assertEqual(1, self._events["counter7_complete"])

        # Test setting the value with direction down counter
        reset_event_mocks()
        self.assertEqual(0, self._events["counter7_complete"])
        self.post_event("set_counter7_negative25")
        self.assertEqual(1, self._events["counter7_complete"])
        self.post_event("set_counter7_0")
        self.assertEqual(2, self._events["counter7_complete"])
        self.post_event("set_counter7_3")
        self.post_event("counter7_count")
        self.assertEventCalledWith("counter7_hit", count=2, hits=3, remaining=2)

        self.assertPlaceholderEvaluates(2, "device.counters.counter7.value")

        # nothing happens because machine.test2 is undefined
        self.post_event("set_counter_placeholder")
        self.assertPlaceholderEvaluates(2, "device.counters.counter7.value")

        self.machine.variables.set_machine_var("test2", 4)
        self.post_event("set_counter_placeholder")
        self.assertPlaceholderEvaluates(4, "device.counters.counter7.value")

        self.post_event("subtract_counter_placeholder")
        self.assertPlaceholderEvaluates(4, "device.counters.counter7.value")

        self.machine.variables.set_machine_var("test3", 3)
        self.post_event("subtract_counter_placeholder")
        self.assertPlaceholderEvaluates(1, "device.counters.counter7.value")

        self.post_event("add_counter_placeholder")
        self.assertPlaceholderEvaluates(1, "device.counters.counter7.value")

        self.machine.variables.set_machine_var("test4", 1)
        self.post_event("add_counter_placeholder")
        self.assertPlaceholderEvaluates(2, "device.counters.counter7.value")

    def test_logic_block_outside_game(self):
        self.mock_event("logicblock_accrual2_complete")

        # should work before game
        self.post_event("accrual2_step1")
        self.post_event("accrual2_step2")
        self.assertEqual(1, self._events["logicblock_accrual2_complete"])
        self.post_event("accrual2_restart")

        self.start_game()
        # should work during game
        self.post_event("accrual2_step1")
        self.post_event("accrual2_step2")
        self.assertEqual(2, self._events["logicblock_accrual2_complete"])
        self.post_event("accrual2_restart")

        self.stop_game()

        # should work after game
        self.post_event("accrual2_step1")
        self.post_event("accrual2_step2")
        self.assertEqual(3, self._events["logicblock_accrual2_complete"])

    def test_no_reset_on_complete(self):
        self.mock_event("logicblock_accrual3_complete")

        # start game
        self.start_game()
        # and enable
        self.post_event("accrual3_enable")

        # should work once
        self.post_event("accrual3_step1")
        self.post_event("accrual3_step2")
        self.assertEqual(1, self._events["logicblock_accrual3_complete"])

        # but not a second time because it disabled
        self.post_event("accrual3_step1")
        self.post_event("accrual3_step2")
        self.assertEqual(1, self._events["logicblock_accrual3_complete"])

        # enable again
        self.post_event("accrual3_enable")

        # still completed
        self.post_event("accrual3_step1")
        self.post_event("accrual3_step2")
        self.assertEqual(1, self._events["logicblock_accrual3_complete"])

        # should work after reset
        self.post_event("accrual3_reset")
        self.post_event("accrual3_step1")
        self.post_event("accrual3_step2")
        self.assertEqual(2, self._events["logicblock_accrual3_complete"])

        # disabled again
        self.post_event("accrual3_reset")
        self.post_event("accrual3_step1")
        self.post_event("accrual3_step2")
        self.assertEqual(2, self._events["logicblock_accrual3_complete"])

        # works after enable
        self.post_event("accrual3_enable")
        self.post_event("accrual3_step1")
        self.post_event("accrual3_step2")
        self.assertEqual(3, self._events["logicblock_accrual3_complete"])

    def test_no_reset_and_no_disable_on_complete(self):
        self.mock_event("logicblock_accrual4_complete")

        # start game
        self.start_game()
        # and enable
        self.post_event("accrual4_enable")
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.enabled")
        self.assertPlaceholderEvaluates(False, "device.accruals.accrual4.completed")

        # should work once
        self.post_event("accrual4_step1")
        self.post_event("accrual4_step2")
        self.assertEqual(1, self._events["logicblock_accrual4_complete"])
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.enabled")
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.completed")

        # enabled but still completed
        self.post_event("accrual4_step1")
        self.post_event("accrual4_step2")
        self.assertEqual(1, self._events["logicblock_accrual4_complete"])
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.enabled")
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.completed")

        # should work after reset
        self.post_event("accrual4_reset")
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.enabled")
        self.assertPlaceholderEvaluates(False, "device.accruals.accrual4.completed")
        self.post_event("accrual4_step1")
        self.post_event("accrual4_step2")
        self.assertEqual(2, self._events["logicblock_accrual4_complete"])
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.enabled")
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual4.completed")

    def test_reset_and_no_disable_on_complete(self):
        self.mock_event("logicblock_accrual10_complete")

        # start game
        self.start_game()
        # and enable
        self.post_event("accrual10_enable")
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual10.enabled")
        self.assertPlaceholderEvaluates(False, "device.accruals.accrual10.completed")

        # should work once
        self.post_event("accrual10_step1")
        self.post_event("accrual10_step2")
        self.assertEqual(1, self._events["logicblock_accrual10_complete"])

        # and instantly reset and work again
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual10.enabled")
        self.assertPlaceholderEvaluates(False, "device.accruals.accrual10.completed")
        self.post_event("accrual10_step1")
        self.post_event("accrual10_step2")
        self.assertEqual(2, self._events["logicblock_accrual10_complete"])
        self.assertPlaceholderEvaluates(True, "device.accruals.accrual10.enabled")
        self.assertPlaceholderEvaluates(False, "device.accruals.accrual10.completed")

    def test_player_change(self):
        self.mock_event("logicblock_accrual5_complete")

        self.machine.config['game']['balls_per_game'] = self.machine.placeholder_manager.build_int_template(2)

        self.start_two_player_game()
        self.advance_time_and_run()
        self.post_event("start_mode1")
        self.advance_time_and_run(.1)

        # should work during game - player1
        self.assertEqual(1, self.machine.game.player.number)
        self.post_event("accrual5_step1")
        self.post_event("accrual5_step2")
        self.assertEqual(1, self._events["logicblock_accrual5_complete"])

        # player2
        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.post_event("start_mode1")
        self.advance_time_and_run(.1)

        # not yet complete
        self.post_event("accrual5_step1")
        self.assertEqual(1, self._events["logicblock_accrual5_complete"])

        # player1 again
        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.post_event("start_mode1")
        self.advance_time_and_run(.1)

        # nothing should happen because its disabled and completed for player1
        self.post_event("accrual5_step1")
        self.post_event("accrual5_step2")
        self.assertEqual(1, self._events["logicblock_accrual5_complete"])

        # player2 again
        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.post_event("start_mode1")
        self.advance_time_and_run(.1)

        # complete it
        self.post_event("accrual5_step2")
        self.assertEqual(2, self._events["logicblock_accrual5_complete"])

        self.post_event("stop_mode1")
        self.stop_game()

        # does not work after game
        self.post_event("accrual5_step1")
        self.post_event("accrual5_step2")
        self.assertEqual(2, self._events["logicblock_accrual5_complete"])

    def test_counter_hit_window(self):
        self.start_game()
        self.mock_event("logicblock_counter3_complete")
        self.mock_event("counter_counter3_hit")

        self.post_event("counter3_enable")
        for i in range(10):
            self.post_event("counter3_count")
            self.assertEqual(0, self._events["logicblock_counter3_complete"])

        # inside same window. only one hit
        self.assertEqual(1, self._events["counter_counter3_hit"])
        self.assertEqual(0, self._events["logicblock_counter3_complete"])
        self.advance_time_and_run(1)

        for i in range(3):
            self.post_event("counter3_count")
            self.assertEqual(0, self._events["logicblock_counter3_complete"])
            self.assertEqual(2 + i, self._events["counter_counter3_hit"])
            self.advance_time_and_run(1)

        # it should complete
        self.post_event("counter3_count")
        self.assertEqual(1, self._events["logicblock_counter3_complete"])
        self.assertEqual(5, self._events["counter_counter3_hit"])

    def test_counter_template(self):
        self.start_game()
        self.mock_event("logicblock_counter4_complete")
        self.mock_event("counter_counter4_hit")

        self.machine.game.player.hits = 2

        self.post_event("counter4_enable")
        for i in range(2):
            self.assertEqual(0, self._events["logicblock_counter4_complete"])
            self.post_event("counter4_count")

        self.assertEqual(2, self._events["counter_counter4_hit"])
        self.assertEqual(1, self._events["logicblock_counter4_complete"])
        self.advance_time_and_run(1)

        self.machine.variables.set_machine_var("start", 1)
        self.machine.game.player.hits = 5
        self.mock_event("logicblock_counter4_complete")
        self.mock_event("counter_counter4_hit")

        self.post_event("counter4_reset")
        self.post_event("counter4_enable")
        for i in range(4):
            self.assertEqual(0, self._events["logicblock_counter4_complete"])
            self.post_event("counter4_count")

        # inside same window. only one hit
        self.assertEqual(4, self._events["counter_counter4_hit"])
        self.assertEqual(1, self._events["logicblock_counter4_complete"])
        self.advance_time_and_run(1)

    def test_counter_persist(self):
        self.mock_event("logicblock_counter_persist_complete")
        self.mock_event("counter_counter_persist_hit")
        self.start_two_player_game()
        self.post_event("start_mode1")
        self.assertTrue("mode1" in self.machine.modes)
        self.post_event("counter_persist_enable")

        for i in range(3):
            self.post_event("counter_persist_count")
            self.assertEqual(i + 1, self._events["counter_counter_persist_hit"])

        self.assertEqual(0, self._events["logicblock_counter_persist_complete"])

        self.drain_all_balls()
        self.assertPlayerNumber(2)

        for i in range(10):
            self.post_event("counter_persist_count")

        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.post_event("start_mode1")
        self.post_event("counter_persist_enable")

        self.assertEqual(0, self._events["logicblock_counter_persist_complete"])

        for i in range(2):
            self.post_event("counter_persist_count")
            self.assertEqual(i + 4, self._events["counter_counter_persist_hit"])

        self.assertEqual(1, self._events["logicblock_counter_persist_complete"])

    def test_count_without_end(self):
        self.start_game()
        self.post_event("counter5_count")
        self.post_event("counter5_count")
        self.post_event("counter5_count")

        self.assertEqual(3, self.machine.counters["counter5"].value)
