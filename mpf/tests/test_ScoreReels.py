"""Test score reels."""
from unittest.mock import MagicMock

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestScoreReels(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/score_reels/'

    def _synchronise_to_reel(self):
        pass

    def testOvershooting(self):
        player1_10k = self.machine.coils["player1_10k"].hw_driver
        player1_1k = self.machine.coils["player1_1k"].hw_driver
        player1_100 = self.machine.coils["player1_100"].hw_driver
        player1_10 = self.machine.coils["player1_10"].hw_driver
        chime1 = self.machine.coils["chime1"].hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        chime1.pulse = MagicMock(return_value=10)

        self._synchronise_to_reel()
        # reel desyncs while idle
        self.release_switch_and_run("score_1p_10_0", 0)

        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # resynced
        self.hit_switch_and_run("score_1p_10_0", 0)
        self.advance_time_and_run(10)

        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # advance one position
        self.machine.score_reels["score_1p_100"].set_destination_value(1)
        self.advance_time_and_run(.02)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # success
        self.release_switch_and_run("score_1p_100_0", 0)
        self.advance_time_and_run(10)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # the reel jumps back (for some reason)
        self.hit_switch_and_run("score_1p_100_0", 0)
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(2, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # resync
        self.release_switch_and_run("score_1p_100_0", 0)
        self.advance_time_and_run(10)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(2, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

    def testScoring(self):
        player1_10k = self.machine.coils["player1_10k"].hw_driver
        player1_1k = self.machine.coils["player1_1k"].hw_driver
        player1_100 = self.machine.coils["player1_100"].hw_driver
        player1_10 = self.machine.coils["player1_10"].hw_driver
        chime1 = self.machine.coils["chime1"].hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        chime1.pulse = MagicMock(return_value=10)

        self.start_game()
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.advance_time_and_run()
        self._synchronise_to_reel()
        self.machine.game.player.score = 110
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.hit_switch_and_run("score_1p_10k_0", 0)
        self.hit_switch_and_run("score_1p_1k_0", 0)
        self.release_switch_and_run("score_1p_100_0", 0)
        self.release_switch_and_run("score_1p_10_0", 0)

        self.advance_time_and_run(10)

        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.assertEqual(0, chime1.pulse.call_count)
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)

        self._synchronise_to_reel()
        self.machine.game.player.score = 11207
        self.advance_time_and_run(.005)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        self.advance_time_and_run(.02)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        self.advance_time_and_run(.02)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(1, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        self.advance_time_and_run(.02)
        self.assertEqual(1, player1_10k.pulse.call_count)
        self.assertEqual(1, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        self.release_switch_and_run("score_1p_10k_0", 0)
        self.release_switch_and_run("score_1p_1k_0", 0)

        self.advance_time_and_run(.17)
        self.assertEqual(2, player1_10.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)

        self.advance_time_and_run(.2)
        self.assertEqual(1, chime1.pulse.call_count)
        self.assertEqual(3, player1_10.pulse.call_count)

        self.advance_time_and_run(.2)
        self.assertEqual(4, player1_10.pulse.call_count)

        self.advance_time_and_run(.2)
        self.assertEqual(5, player1_10.pulse.call_count)

        self.advance_time_and_run(.2)
        self.assertEqual(6, player1_10.pulse.call_count)

        self.advance_time_and_run(.2)
        self.assertEqual(7, player1_10.pulse.call_count)

        self.advance_time_and_run(.2)
        self.assertEqual(1, player1_10k.pulse.call_count)
        self.assertEqual(1, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(8, player1_10.pulse.call_count)

        # it was stuck somewhere before 9
        self.advance_time_and_run(.2)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)

        self.advance_time_and_run(.1)
        self.hit_switch_and_run("score_1p_10_9", 0)
        self.advance_time_and_run(.1)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(10, player1_10.pulse.call_count)

        self.advance_time_and_run(.1)
        self.release_switch_and_run("score_1p_10_9", 0)
        self.hit_switch_and_run("score_1p_10_0", 0)
        self.advance_time_and_run(.1)

        # no more changes
        self.advance_time_and_run(10)
        self.assertEqual(1, player1_10k.pulse.call_count)
        self.assertEqual(1, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(10, player1_10.pulse.call_count)
        self.assertEqual(1, chime1.pulse.call_count)

    def testAdvanceingFailure(self):
        player1_10k = self.machine.coils["player1_10k"].hw_driver
        player1_1k = self.machine.coils["player1_1k"].hw_driver
        player1_100 = self.machine.coils["player1_100"].hw_driver
        player1_10 = self.machine.coils["player1_10"].hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        self.start_game()

        self._synchronise_to_reel()
        self.machine.game.player.score += 110
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.release_switch_and_run("score_1p_10_0", 0)
        # switch for pos 0 stays on

        # it retries
        self.advance_time_and_run(.25)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(2, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # and again
        self.advance_time_and_run(.25)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(3, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        # finally
        self.release_switch_and_run("score_1p_100_0", 0)

        # no more retries
        self.advance_time_and_run(10)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(3, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

    def testThreePlayers(self):
        player1_10k = self.machine.coils["player1_10k"].hw_driver
        player1_1k = self.machine.coils["player1_1k"].hw_driver
        player1_100 = self.machine.coils["player1_100"].hw_driver
        player1_10 = self.machine.coils["player1_10"].hw_driver
        player2_10 = self.machine.coils["player2_10"].hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        player2_10.pulse = MagicMock(return_value=10)
        self.start_game()

        # add two more players
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertEqual(3, self.machine.game.num_players)

        self._synchronise_to_reel()
        self.machine.game.player.score += 110
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.release_switch_and_run("score_1p_10_0", 0)
        self.release_switch_and_run("score_1p_100_0", 0)

        # no more fires
        self.advance_time_and_run(10)
        self.machine_run()
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # drain ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(.1)
        self.assertEqual(2, self.machine.game.player.number)

        self.machine.game.player.score += 20
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.assertEqual(1, player2_10.pulse.call_count)
        self.release_switch_and_run("score_2p_10_0", 0)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)

        # no more changes
        self.advance_time_and_run(10)
        self.machine_run()
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)

        # drain ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(.15)
        self.assertEqual(3, self.machine.game.player.number)

        # player3 reuses the reels from player 1. machine resets them
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(2, player1_100.pulse.call_count)
        self.assertEqual(2, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)

        for i in range(7):
            self.advance_time_and_run(.2)

        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(9, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)

        self.hit_switch_and_run("score_1p_10_9", 0)
        self.hit_switch_and_run("score_1p_100_9", 0)

        self.advance_time_and_run(.2)

        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(10, player1_100.pulse.call_count)
        self.assertEqual(10, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)

        self.hit_switch_and_run("score_1p_10_0", 0)
        self.hit_switch_and_run("score_1p_100_0", 0)
        self.release_switch_and_run("score_1p_10_9", 0)
        self.release_switch_and_run("score_1p_100_9", 0)

        self.advance_time_and_run(10)

        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(10, player1_100.pulse.call_count)
        self.assertEqual(10, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)


class TestScoreReelsVirtual(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_platform(self):
        return "smart_virtual"

    def get_machine_path(self):
        return 'tests/machine_files/score_reels/'

    def testScoringVirtual(self):
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")

        # wait for reset of score reels
        self.advance_time_and_run(4)
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)

        self.advance_time_and_run()
        self.assertSwitchState("score_1p_10_0", 1)
        self.assertSwitchState("score_1p_100_0", 1)
        self.assertSwitchState("score_1p_10_9", 0)
        self.assertSwitchState("score_1p_100_9", 0)

        self.machine.game.player.score += 110
        self.advance_time_and_run(10)

        self.assertSwitchState("score_1p_10_0", 0)
        self.assertSwitchState("score_1p_100_0", 0)
        self.assertSwitchState("score_1p_10_9", 0)
        self.assertSwitchState("score_1p_100_9", 0)

        self.machine.game.player.score = 990
        self.advance_time_and_run(10)

        self.assertSwitchState("score_1p_10_0", 0)
        self.assertSwitchState("score_1p_100_0", 0)
        self.assertSwitchState("score_1p_10_9", 1)
        self.assertSwitchState("score_1p_100_9", 1)

        self.machine.game.player.score = 1900
        self.advance_time_and_run(10)

        self.assertSwitchState("score_1p_10_0", 1)
        self.assertSwitchState("score_1p_100_0", 0)
        self.assertSwitchState("score_1p_10_9", 0)
        self.assertSwitchState("score_1p_100_9", 1)

    def test_inactive_player_scoring(self):
        self.start_two_player_game()
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)

        self.advance_time_and_run()
        self.assertEqual([None, 0, 0, 0, 0], self.machine.score_reel_groups["player1"].desired_value_list)
        self.assertEqual([None, 0], self.machine.score_reel_groups["player2"].desired_value_list)

        # increasing score for player two should only affect score of that player
        self.machine.game.player_list[1].score = 3333
        self.advance_time_and_run()
        self.assertEqual([None, 0, 0, 0, 0], self.machine.score_reel_groups["player1"].desired_value_list)
        self.assertEqual([None, 3], self.machine.score_reel_groups["player2"].desired_value_list)

        self.machine.game.player_list[0].score = 2222
        self.advance_time_and_run()
        self.assertEqual([None, 2, 2, 2, 0], self.machine.score_reel_groups["player1"].desired_value_list)
        self.assertEqual([None, 3], self.machine.score_reel_groups["player2"].desired_value_list)

        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.assertBallNumber(1)

        self.machine.game.player_list[0].score = 4444
        self.advance_time_and_run()
        self.assertEqual([None, 4, 4, 4, 0], self.machine.score_reel_groups["player1"].desired_value_list)
        self.assertEqual([None, 3], self.machine.score_reel_groups["player2"].desired_value_list)

        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        self.drain_all_balls()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        self.drain_all_balls()
        self.assertGameIsNotRunning()

        # start game. we cannot use start_two_player_game because score reels block the start for some seconds
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsRunning()
        self.assertEqual(0, self.machine.game.num_players)
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.game.num_players)
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.game.num_players)
        self.assertPlayerNumber(1)

        self.assertEqual([None, 0, 0, 0, 0], self.machine.score_reel_groups["player1"].desired_value_list)
        self.assertEqual([None, 0], self.machine.score_reel_groups["player2"].desired_value_list)
