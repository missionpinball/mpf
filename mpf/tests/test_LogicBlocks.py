"""Test logic blocks."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestLogicBlocks(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
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
            self.assertEventCalledWith("counter2_hit", count=i + 1, remaining=2 - i)

        self.post_event("counter2_count")
        self.assertEqual(1, self._events["counter2_complete"])
        self.assertEventCalledWith("counter2_hit", count=3, remaining=0)

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

        # should work once
        self.post_event("accrual4_step1")
        self.post_event("accrual4_step2")
        self.assertEqual(1, self._events["logicblock_accrual4_complete"])

        # enabled but still completed
        self.post_event("accrual4_step1")
        self.post_event("accrual4_step2")
        self.assertEqual(1, self._events["logicblock_accrual4_complete"])

        # should work after reset
        self.post_event("accrual4_reset")
        self.post_event("accrual4_step1")
        self.post_event("accrual4_step2")
        self.assertEqual(2, self._events["logicblock_accrual4_complete"])

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

        self.machine.set_machine_var("start", 1)
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

        self.assertEqual(3, self.machine.counters.counter5.value)
