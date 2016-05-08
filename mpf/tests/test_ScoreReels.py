from mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestShots(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/score_reels/'

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

        self.machine.scoring.add(11097)  # result: 11207
        self.advance_time_and_run(.1)
        self.advance_time_and_run(.1)
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(1, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(2, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(3, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(4, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(5, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(6, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(7, player1_10.pulse.call_count)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(0, player1_100.pulse.call_count)
        self.assertEqual(8, player1_10.pulse.call_count)
        self.hit_switch_and_run("score_1p_10_9", 0)

        self.advance_time_and_run(.3)
        self.machine_run()
        self.assertEqual(0, player1_10k.pulse.call_count)
        self.assertEqual(0, player1_1k.pulse.call_count)
        self.assertEqual(1, player1_100.pulse.call_count)
        self.assertEqual(9, player1_10.pulse.call_count)

        self.release_switch_and_run("score_1p_10_9", 0)
        self.hit_switch_and_run("score_1p_10_0", 0)

        # only two coils at a time. postpone 1k and 10k
        self.advance_time_and_run(.2)
        self.machine_run()
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
