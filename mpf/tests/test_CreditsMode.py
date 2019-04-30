from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase, test_config


class TestCreditsMode(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/credits/'

    def start_game(self, should_work):
        # shots only work in games so we have to do this a lot
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        if should_work:
            self.assertIsNotNone(self.machine.game)
            self.machine.game.balls_in_play = 0
            self.advance_time_and_run()
        else:
            self.assertIsNone(self.machine.game)

    def start_two_player_game(self):
        # game start should work
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(1, self.machine.game.num_players)

        # add another player
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.game.num_players)

    def stop_game(self):
        # stop game
        self.assertIsNotNone(self.machine.game)
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    @test_config("config_freeplay.yaml")
    def test_free_play_at_start(self):
        self.assertEqual("FREE PLAY", self.machine.get_machine_var('credits_string'))
        self.assertFalse(self.machine.is_machine_var("price_per_game_raw_0"))
        self.assertFalse(self.machine.is_machine_var("price_per_game_string_0"))

        self.start_two_player_game()

    def testToggleEvents(self):
        self.assertTrue(self.machine.mode_controller.is_active('credits'))
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        self.post_event("toggle_credit_play")
        self.assertEqual("FREE PLAY", self.machine.get_machine_var('credits_string'))

        self.post_event("toggle_credit_play")
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        self.start_game(False)

        self.post_event("toggle_credit_play")
        self.assertEqual("FREE PLAY", self.machine.get_machine_var('credits_string'))

        self.start_two_player_game()
        self.stop_game()

        self.post_event("enable_credit_play")
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        self.post_event("enable_credit_play")
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        self.post_event("enable_free_play")
        self.assertEqual("FREE PLAY", self.machine.get_machine_var('credits_string'))

        self.post_event("enable_free_play")
        self.assertEqual("FREE PLAY", self.machine.get_machine_var('credits_string'))

    def testCredits(self):
        self.assertTrue(self.machine.mode_controller.is_active('credits'))
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        # no credits no game
        self.start_game(False)

        self.hit_and_release_switch("s_left_coin")
        self.machine_run()

        self.assertEqual("CREDITS 1/2", self.machine.get_machine_var('credits_string'))

        self.assertMachineVarEqual(0.5, "price_per_game_raw_0")
        self.assertMachineVarEqual("1 CREDITS $0.5", "price_per_game_string_0")
        self.assertMachineVarEqual(2, "price_per_game_raw_1")
        self.assertMachineVarEqual("5 CREDITS $2.0", "price_per_game_string_1")

        # not enough credits. no game
        self.start_game(False)

        self.hit_and_release_switch("s_left_coin")
        self.machine_run()

        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))

        # one is enough for a game
        self.start_game(True)
        self.stop_game()

        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        # but only one
        self.start_game(False)

        self.hit_and_release_switch("s_right_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2", self.machine.get_machine_var('credits_string'))

        # no more price tier after game
        self.hit_and_release_switch("s_left_coin")
        self.hit_and_release_switch("s_left_coin")
        self.machine_run()
        self.assertEqual("CREDITS 3", self.machine.get_machine_var('credits_string'))

    def testReplay(self):
        # add coins
        self.hit_and_release_switch("s_left_coin")
        self.hit_and_release_switch("s_left_coin")
        self.advance_time_and_run()
        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))
        # start game
        self.start_game(True)

        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))
        # no replay
        self.stop_game()

        # try again
        self.hit_and_release_switch("s_left_coin")
        self.hit_and_release_switch("s_left_coin")
        self.advance_time_and_run()
        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))
        self.start_game(True)

        # score 600k
        self.machine.game.player.score = 600000

        # replay credit on game end
        self.stop_game()
        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))

    def testMorePlayers(self):
        self.assertTrue(self.machine.mode_controller.is_active('credits'))
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        self.hit_and_release_switch("s_left_coin")
        self.hit_and_release_switch("s_left_coin")
        self.machine_run()

        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))

        # one is enough for a game
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertIsNotNone(self.machine.game)

        # no more credits
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))
        self.assertEqual(1, self.machine.game.num_players)
        # try to add another player
        self.hit_and_release_switch("s_start")
        # fails
        self.assertEqual(1, self.machine.game.num_players)

        # add credits
        self.hit_and_release_switch("s_right_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2", self.machine.get_machine_var('credits_string'))

        # try to add another player
        self.hit_and_release_switch("s_start")
        # wrorks
        self.assertEqual(2, self.machine.game.num_players)
        self.machine_run()
        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))

    def testMaxCredits(self):
        self.assertTrue(self.machine.mode_controller.is_active('credits'))
        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        self.hit_and_release_switch("s_right_coin")
        self.hit_and_release_switch("s_right_coin")
        self.hit_and_release_switch("s_right_coin")
        self.hit_and_release_switch("s_right_coin")
        self.machine_run()

        self.assertEqual("CREDITS 10", self.machine.get_machine_var('credits_string'))

        self.hit_and_release_switch("s_right_coin")
        self.machine_run()
        self.assertEqual("CREDITS 12", self.machine.get_machine_var('credits_string'))

        self.hit_and_release_switch("s_right_coin")
        self.machine_run()
        self.assertEqual("CREDITS 12", self.machine.get_machine_var('credits_string'))

    def testPricingTiers(self):
        self.hit_and_release_switch("s_right_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2", self.machine.get_machine_var('credits_string'))

        self.hit_and_release_switch("s_right_coin")
        self.machine_run()
        self.assertEqual("CREDITS 5", self.machine.get_machine_var('credits_string'))

    def testFractionalTimeout(self):
        self.hit_and_release_switch("s_right_coin")
        self.hit_and_release_switch("s_left_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2 1/2", self.machine.get_machine_var('credits_string'))

        self.advance_time_and_run(60 * 15)

        self.assertEqual("CREDITS 2", self.machine.get_machine_var('credits_string'))

        # but not during game
        self.hit_and_release_switch("s_left_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2 1/2", self.machine.get_machine_var('credits_string'))

        self.start_game(True)
        self.advance_time_and_run(60 * 15)
        self.stop_game()

        self.machine_run()
        self.assertEqual("CREDITS 1 1/2", self.machine.get_machine_var('credits_string'))

        # but timeout restarts
        self.advance_time_and_run(60 * 15)

        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))

    def testCreditTimeout(self):
        self.hit_and_release_switch("s_right_coin")
        self.hit_and_release_switch("s_left_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2 1/2", self.machine.get_machine_var('credits_string'))

        self.advance_time_and_run(3600 * 2)

        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

        # but not during game
        self.hit_and_release_switch("s_right_coin")
        self.hit_and_release_switch("s_left_coin")
        self.machine_run()
        self.assertEqual("CREDITS 2 1/2", self.machine.get_machine_var('credits_string'))

        self.start_game(True)
        self.advance_time_and_run(3600 * 2)
        self.stop_game()

        self.machine_run()
        self.assertEqual("CREDITS 1 1/2", self.machine.get_machine_var('credits_string'))

        # but timeout restarts
        self.advance_time_and_run(3600 * 2)

        self.assertEqual("CREDITS 0", self.machine.get_machine_var('credits_string'))

    def testServiceCredits(self):
        self.hit_and_release_switch("s_esc")
        self.machine_run()
        self.assertEqual("CREDITS 1", self.machine.get_machine_var('credits_string'))
