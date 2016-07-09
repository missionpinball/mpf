"""Test score reels."""
from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestScoreReels(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/score_reels/'

    def _synchronise_to_reel(self):
        ts =  self.machine.score_reel_groups.player1._tick_task.get_next_call_time()
        self.assertTrue(ts)
        self.advance_time_and_run(ts - self.machine.clock.get_time())
        self.advance_time_and_run(.01)

    def start_game(self):
        # shots only work in games so we have to do this a lot
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertIsNotNone(self.machine.game)

    def stop_game(self):
        # stop game
        self.assertIsNotNone(self.machine.game)
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def testScoring(self):
        player1_10k = self.machine.coils.player1_10k.hw_driver
        player1_1k = self.machine.coils.player1_1k.hw_driver
        player1_100 = self.machine.coils.player1_100.hw_driver
        player1_10 = self.machine.coils.player1_10.hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        self.start_game()

        self._synchronise_to_reel()
        self.machine.scoring.add(110)
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
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)

        self._synchronise_to_reel()
        self.machine.scoring.add(11097)  # result: 11207
        self.advance_time_and_run(.05)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        self.advance_time_and_run(.4)
        self.assertEqual(2, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.assertEqual(3, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.assertEqual(4, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.assertEqual(5, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.assertEqual(6, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.assertEqual(7, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(8, player1_10.pulse.call_count)
        self.hit_switch_and_run("score_1p_10_9", 0)

        self.advance_time_and_run(.3)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)

        self.release_switch_and_run("score_1p_10_9", 0)
        self.hit_switch_and_run("score_1p_10_0", 0)

        # only two coils at a time. postpone 1k and 10k
        self.advance_time_and_run(.1)
        self.assertEqual(1, player1_10k.pulse.call_count)
        self.assertEqual(1, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)

        self.release_switch_and_run("score_1p_10k_0", 0)
        self.release_switch_and_run("score_1p_1k_0", 0)

        self.advance_time_and_run(.5)
        self.assertEqual(1, player1_10k.pulse.call_count)
        self.assertEqual(1, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)

    def testAdvanceingFailure(self):
        player1_10k = self.machine.coils.player1_10k.hw_driver
        player1_1k = self.machine.coils.player1_1k.hw_driver
        player1_100 = self.machine.coils.player1_100.hw_driver
        player1_10 = self.machine.coils.player1_10.hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        self.start_game()

        self._synchronise_to_reel()
        self.machine.scoring.add(110)
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)
        self.release_switch_and_run("score_1p_10_0", 0)
        # switch for pos 0 stays on

        # it retries
        self.advance_time_and_run(.4)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(2, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        # and again
        self.advance_time_and_run(.4)
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
        player1_10k = self.machine.coils.player1_10k.hw_driver
        player1_1k = self.machine.coils.player1_1k.hw_driver
        player1_100 = self.machine.coils.player1_100.hw_driver
        player1_10 = self.machine.coils.player1_10.hw_driver
        player2_10 = self.machine.coils.player2_10.hw_driver
        player1_10k.pulse = MagicMock(return_value=10)
        player1_1k.pulse = MagicMock(return_value=10)
        player1_100.pulse = MagicMock(return_value=10)
        player1_10.pulse = MagicMock(return_value=10)
        player2_10.pulse = MagicMock(return_value=10)
        self.start_game()

        # add two more players
        self.hit_and_release_switch("s_start")
        self.hit_and_release_switch("s_start")
        self.machine_run()
        self.assertEqual(3, self.machine.game.num_players)

        self._synchronise_to_reel()
        self.machine.scoring.add(110)
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
        self.machine_run()
        self.assertEqual(2, self.machine.game.player.number)

        self.machine.scoring.add(20)
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
            self.advance_time_and_run(.3)

        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(9, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)
        self.assertEqual(2, player2_10.pulse.call_count)

        self.hit_switch_and_run("score_1p_10_9", 0)
        self.hit_switch_and_run("score_1p_100_9", 0)

        self.advance_time_and_run(.3)

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
