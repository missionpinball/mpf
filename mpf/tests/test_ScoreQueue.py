from unittest.mock import MagicMock

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestScoreQueue(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/score_queue/'

    def test_score_queue(self):
        """Test the score queue for SS games."""
        # try a score outside of a game. should not crash
        self.machine.score_queues["score"].score(2000)
        self.advance_time_and_run()

        # start game with two players
        self.start_two_player_game()
        self.machine.coils["c_chime_1000"].pulse = MagicMock()
        self.machine.coils["c_chime_100"].pulse = MagicMock()
        self.machine.coils["c_chime_10"].pulse = MagicMock()

        self.assertPlayerVarEqual(0, "score")
        self.machine.score_queues["score"].score(2100)
        self.machine.score_queues["score"].score(20)
        # first queue entry
        self.advance_time_and_run(.1)
        self.assertPlayerVarEqual(1000, "score")
        self.machine.coils["c_chime_1000"].pulse.assert_called_with()
        self.machine.coils["c_chime_1000"].pulse = MagicMock()
        self.advance_time_and_run(.2)
        self.assertPlayerVarEqual(2000, "score")
        self.machine.coils["c_chime_1000"].pulse.assert_called_with()
        self.machine.coils["c_chime_1000"].pulse = MagicMock()
        self.machine.coils["c_chime_100"].pulse.assert_not_called()
        self.advance_time_and_run(.2)
        self.assertPlayerVarEqual(2100, "score")
        self.machine.coils["c_chime_100"].pulse.assert_called_with()
        self.machine.coils["c_chime_100"].pulse = MagicMock()
        self.machine.coils["c_chime_1000"].pulse.assert_not_called()
        self.machine.coils["c_chime_10"].pulse.assert_not_called()
        self.advance_time_and_run(.2)
        # second queue entry now
        self.assertPlayerVarEqual(2110, "score")
        self.machine.coils["c_chime_10"].pulse.assert_called_with()
        self.machine.coils["c_chime_10"].pulse = MagicMock()
        self.machine.coils["c_chime_1000"].pulse.assert_not_called()
        self.machine.coils["c_chime_100"].pulse.assert_not_called()
        self.advance_time_and_run(.2)
        self.assertPlayerVarEqual(2120, "score")
        self.machine.coils["c_chime_10"].pulse.assert_called_with()
        self.machine.coils["c_chime_10"].pulse = MagicMock()
        self.machine.coils["c_chime_1000"].pulse.assert_not_called()
        self.machine.coils["c_chime_100"].pulse.assert_not_called()

        # no more
        self.advance_time_and_run(1)
        self.assertPlayerVarEqual(2120, "score")
        self.machine.coils["c_chime_1000"].pulse.assert_not_called()
        self.machine.coils["c_chime_100"].pulse.assert_not_called()
        self.machine.coils["c_chime_10"].pulse.assert_not_called()

        # test scoring during drain
        self.machine.score_queues["score"].score(90)
        self.drain_all_balls()

        self.advance_time_and_run(2)
        self.assertEqual(2210, self.machine.game.player_list[0].score)
        self.assertEqual(0, self.machine.game.player_list[1].score)

        self.assertPlayerNumber(2)
        self.machine.score_queues["score"].score(90)
        self.advance_time_and_run(2)
        self.assertEqual(2210, self.machine.game.player_list[0].score)
        self.assertEqual(90, self.machine.game.player_list[1].score)

        self.start_mode("mode1")
        self.post_event("score_2k")
        self.post_event("score_200")
        self.advance_time_and_run(2)
        self.assertEqual(2210, self.machine.game.player_list[0].score)
        self.assertEqual(2290, self.machine.game.player_list[1].score)
