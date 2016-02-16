from mpf.tests.MpfTestCase import MpfTestCase


class TestLogicBlocks(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/logic_blocks/'

    def _start_game(self):
        self.machine.ball_controller.num_balls_known = 0
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.advance_time_and_run(2)

        # start game
        self.hit_and_release_switch("s_start")
        self.assertNotEqual(None, self.machine.game)

    # TODO: should it complete again when enabled but not reset?

    def test_accruals_simple(self):
        self._start_game()
        self.mock_event("accrual1_complete1")
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

        # step1
        self.post_event("accrual1_step1c")
        self.post_event("accrual1_step1b")
        self.assertEqual(0, self._events["accrual1_complete1"])

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
        self._start_game()
        self.mock_event("counter1_complete")
        self.mock_event("counter1_hit")

        self.post_event("counter1_enable")
        for i in range(4):
            self.post_event("counter1_count")
            self.assertEqual(0, self._events["counter1_complete"])

        # nothing should happen when disabled
        self.post_event("counter1_disable")
        for i in range(10):
            self.post_event("counter1_count")
            self.assertEqual(0, self._events["counter1_complete"])
        self.post_event("counter1_enable")

        self.post_event("counter1_count")
        self.assertEqual(1, self._events["counter1_complete"])
        self.assertEqual(5, self._events["counter1_hit"])

        # it should disable
        self.post_event("counter1_count")
        self.assertEqual(1, self._events["counter1_complete"])
        self.assertEqual(5, self._events["counter1_hit"])

        self.post_event("counter1_enable")
        self.post_event("counter1_reset")

        for i in range(4):
            self.post_event("counter1_count")

        # 4 more hits but not completed
        self.assertEqual(1, self._events["counter1_complete"])
        self.assertEqual(9, self._events["counter1_hit"])

        # reset
        self.post_event("counter1_reset")
        for i in range(4):
            self.post_event("counter1_count")

        # another 4 hits still not complete
        self.assertEqual(1, self._events["counter1_complete"])
        self.assertEqual(13, self._events["counter1_hit"])

        # and complete again
        self.post_event("counter1_count")
        self.assertEqual(2, self._events["counter1_complete"])
        self.assertEqual(14, self._events["counter1_hit"])

    def test_sequence_simple(self):
        self._start_game()
        self.mock_event("sequence1_complete")

        self.post_event("sequence1_enable")

        # wrong order
        self.post_event("sequence1_step3a")
        self.post_event("sequence1_step2a")
        self.post_event("sequence1_step1b")
        self.assertEqual(0, self._events["sequence1_complete"])

        # still not
        self.post_event("sequence1_step3b")
        self.post_event("sequence1_step1a")
        self.assertEqual(0, self._events["sequence1_complete"])

        # only 1 so far. now step2
        self.post_event("sequence1_step2a")
        self.assertEqual(0, self._events["sequence1_complete"])

        # and step 3
        self.post_event("sequence1_step3b")
        self.assertEqual(1, self._events["sequence1_complete"])

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