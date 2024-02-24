from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestVariablePlayer(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/variable_player/'

    def test_variable_player(self):
        # start game with two players
        self.start_two_player_game()

        self.assertFalse(self.machine.mode_controller.is_active('mode1'))

        self.post_event("test_event1")
        self.assertEqual(0, self.machine.game.player.score)
        self.assertEqual(0, self.machine.game.player.var_c)

        # start mode 1
        self.post_event('start_mode1')
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))

        self.post_event("test_add_machine_var")
        self.machine_run()
        self.assertMachineVarEqual(23, "my_var")

        self.post_event("test_set_machine_var")
        self.machine_run()
        self.assertMachineVarEqual(100, "my_var")

        self.post_event("test_add_machine_var")
        self.machine_run()
        self.assertMachineVarEqual(123, "my_var")

        # test setting string
        self.post_event('test_set_string')
        self.assertEqual('HELLO', self.machine.game.player.string_test)

        # event should score 100 now
        self.post_event("test_event1")
        self.assertEqual(100, self.machine.game.player.score)
        self.assertEqual(1, self.machine.game.player.vars['var_a'])
        self.assertEqual(0, self.machine.game.player.var_c)
        self.machine.game.player.ramps = 3
        self.assertMachineVarEqual(100, "my_var2")

        self.post_event("test_event1")
        self.assertEqual(200, self.machine.game.player.score)
        self.assertEqual(2, self.machine.game.player.vars['var_a'])
        self.assertEqual(3, self.machine.game.player.var_c)
        self.assertMachineVarEqual(200, "my_var2")

        self.post_event("test_set_100")
        self.assertEqual(100, self.machine.game.player.test1)
        self.post_event("test_set_200")
        self.assertEqual(200, self.machine.game.player.test1)
        self.post_event("test_set_100")
        self.assertEqual(100, self.machine.game.player.test1)

        # start mode 2
        self.post_event('start_mode2')
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))

        # event should score 1000 now (and block the 100 from mode1)
        self.post_event("test_event1")
        self.assertEqual(1200, self.machine.game.player.score)
        # var_a is blocked
        self.assertEqual(2, self.machine.game.player.vars['var_a'])
        # but we count var_b
        self.assertEqual(1, self.machine.game.player.vars['var_b'])
        self.assertEqual(33, self.machine.game.player.var_c)

        # switch players
        self.drain_all_balls()
        self.assertEqual(2, self.machine.game.player.number)

        self.assertEqual(0, self.machine.game.player.score)

        # modes should be unloaded
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.assertFalse(self.machine.mode_controller.is_active('mode2'))

        # mode is unloaded. should not score
        self.post_event("test_event1")
        self.assertEqual(0, self.machine.game.player.score)

        # load mode two
        self.post_event('start_mode2')
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))

        self.post_event("test_event1")
        self.assertEqual(1000, self.machine.game.player.score)
        # var_a is 0
        self.assertEqual(0, self.machine.game.player.var_a)
        # but we count var_b
        self.assertEqual(1, self.machine.game.player.vars['var_b'])

        # switch players again
        self.drain_all_balls()
        self.assertEqual(1, self.machine.game.player.number)

        # mode2 should auto start
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))
        self.assertTrue(self.machine.modes["mode2"].active)

        # same score as during last ball
        self.assertEqual(1200, self.machine.game.player.score)
        self.assertEqual(2, self.machine.game.player.vars['var_a'])
        self.assertEqual(1, self.machine.game.player.vars['var_b'])

        # should still score 1000 points
        self.post_event("test_event1")
        self.assertEqual(2200, self.machine.game.player.score)
        self.assertEqual(2, self.machine.game.player.vars['var_a'])
        self.assertEqual(2, self.machine.game.player.vars['var_b'])

        self.post_event("start_mode3")
        self.advance_time_and_run()

        self.assertPlayerVarEqual(2200, "score")
        self.assertEqual(1000, self.machine.game.player_list[1].score)
        self.post_event("score_player2")
        self.assertPlayerVarEqual(2200, "score")
        self.assertEqual(1023, self.machine.game.player_list[1].score)

        self.post_event("score_player1")
        self.assertPlayerVarEqual(2242, "score")
        self.assertEqual(1023, self.machine.game.player_list[1].score)

        self.post_event("reset_player2")
        self.assertPlayerVarEqual(2242, "score")
        self.assertEqual(10, self.machine.game.player_list[1].score)

        self.post_event("score_float2")
        self.assertPlayerVarEqual(2244, "score")

        self.post_event("set_float")
        self.assertPlayerVarEqual(1.5, "multiplier")

        self.post_event("score_float3")
        self.assertPlayerVarEqual(2394, "score")

        self.post_event("score_floordiv")
        self.assertPlayerVarEqual(125794, "score")

        # should not crash
        self.post_event("set_player7")
        self.post_event("add_player7")

        # stop game and mode
        self.machine.service.start_service()
        self.advance_time_and_run()

        # it should not crash
        self.post_event("test_event1")
        self.advance_time_and_run()

    def test_blocking(self):
        self.machine.variables.set_machine_var("player1_score", 42)
        self.machine.variables.set_machine_var("player2_score", 23)

        # start game
        self.start_game()

        # start mode 1
        self.post_event("start_mode1", 1)

        # test scoring
        self.post_event("test_score_mode", 1)
        # should score 100
        self.assertPlayerVarEqual(100, "score")

        # start mode 2
        self.post_event("start_mode2", 1)

        # test scoring
        self.post_event("test_score_mode", 1)
        # should score 1000 (+ 100 from the previous)
        self.assertPlayerVarEqual(1100, "score")

        self.post_event("stop_mode2", 1)

        # test scoring
        self.post_event("test_score_mode", 1)
        # should score 100 again (+ 1100 from the previous)
        self.assertPlayerVarEqual(1200, "score")

        self.post_event("stop_mode1")
        # we still see the old score here
        self.assertMachineVarEqual(42, "player1_score")

        self.stop_game()

        self.assertMachineVarEqual(1200, "player1_score")
        self.assertFalse(self.machine.variables.is_machine_var("player2_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player4_score"))

    def test_blocking_multiple_with_logic_block(self):
        # this test was adapted from a real game
        # start game
        self.start_game()

        # start mode 1
        self.post_event("start_mode1", 1)

        # hit target 3 times for 10 points each
        # and complete the logic block
        for x in range(0, 3):
            self.hit_and_release_switch("s_counter_target")
        self.assertPlayerVarEqual(30, "score")

        # start mode_for_logic_block
        self.post_event("counter_target_complete")

        # both modes running now
        self.assertModeRunning('mode_for_logic_block')
        self.assertModeRunning('mode1')

        # hit the target while in the new mode
        self.hit_and_release_switch("s_counter_target")
        self.assertPlayerVarEqual(130, "score")

        # trigger the end of the counter_targer mode
        # which also blocks its mode1 scoring this once
        self.hit_and_release_switch("s_kills_counter_target")
        self.assertPlayerVarEqual(630, "score")

        # only mode1 running now
        self.assertModeNotRunning('mode_for_logic_block')
        self.assertModeRunning('mode1')

        # target only scores 10 again... or does it???
        self.hit_and_release_switch("s_counter_target")
        self.assertPlayerVarEqual(640, "score")

    def test_non_game_mode(self):
        # start non game mode outside of game
        self.post_event("start_non_game_mode")

        self.machine.variables.set_machine_var("test", "321")
        self.machine.variables.set_machine_var("test2", 3)

        self.post_event("test_event")

        self.assertMachineVarEqual("123", "test")
        self.assertMachineVarEqual(10, "test2")

        # test subscription
        self.machine.variables.set_machine_var("test5", "123")
        self.advance_time_and_run(.1)
        self.assertMachineVarEqual("123-suffix", "test6")

    def test_event_kwargs(self):
        self.start_game()
        self.post_event('start_mode1')
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))
        self.post_event('start_mode3')
        self.assertTrue(self.machine.mode_controller.is_active('mode3'))

        self.mock_event('player_score')
        self.post_event('test_event1')
        self.advance_time_and_run()
        self.assertEventCalledWith('player_score',
                                    value=100,
                                    prev_value=0,
                                    change=100,
                                    player_num=1,
                                    source='mode1')

        self.post_event('score_player1')
        self.advance_time_and_run()
        self.assertEventCalledWith('player_score',
                                    value=142,
                                    prev_value=100,
                                    change=42,
                                    player_num=1,
                                    source='mode3')
