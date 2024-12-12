"""Test high score mode."""
from unittest.mock import MagicMock, call
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
from mpf.tests.MpfTestCase import test_config_directory


class TestHighScoreMode(MpfBcpTestCase):

    def get_config_file(self):
        return 'high_score.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/high_score/'

    def start_game(self, num_players=1):
        self._bcp_client.send = MagicMock()

        self.machine.playfield.add_ball = MagicMock()
        self.machine.events.post('game_start')
        self.advance_time_and_run()
        self.machine.game.balls_in_play = 1
        self.assertIsNotNone(self.machine.game)

        while self.machine.game.num_players < num_players:
            self.machine.game.request_player_add()
            self.advance_time_and_run()

    def test_high_score_without_game(self):
        # try to start high score mode without a running game
        self.assertIn("high_score", self.machine.modes)
        self.assertModeNotRunning("high_score")
        self.machine.modes["high_score"].start()
        self.advance_time_and_run()
        # mode should not start (neither crash)
        self.assertModeNotRunning("high_score")

    def test_default_high_scores(self):
        new_score_data = dict()
        new_score_data['score'] = [['BRI', 4242],
                                   ['GHK', 2323],
                                   ['JK', 1337],
                                   ['QC', 42],
                                   ['MPF', 23]]
        new_score_data['loops'] = [['JK', 42]]

        self.assertEqual(new_score_data, self.machine.modes["high_score"].high_scores)

    def test_no_high_scores(self):
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 10000]])

        self.start_game(4)
        self.machine.game.player_list[0].score = 1000
        self.machine.game.player_list[1].score = 1000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.advance_time_and_run()
        self.assertFalse(self.machine.modes["high_score"].active)

        new_score_data = dict()
        new_score_data['score'] = [['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890],
                                   ['QC', 87890],
                                   ['MPF', 10000]]
        new_score_data['loops'] = []
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_tilt_during_high_score(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes["high_score"].high_scores = dict(
                            score=[['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890],
                                   ['QC', 87890],
                                   ['MPF', 1000]])

        self.start_game()
        self.advance_time_and_run()
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        # tilt the machine
        self.hit_and_release_switch("s_tilt")
        self.advance_time_and_run()
        self.hit_and_release_switch("s_tilt")
        self.advance_time_and_run()
        self.hit_and_release_switch("s_tilt")
        self.advance_time_and_run()

        # high score should not end
        self.assertTrue(self.machine.modes["high_score"].active)

    def test_reset(self):
        """Test high score reset."""
        self.assertMachineVarEqual('GRAND CHAMPION', "score1_label")
        self.assertMachineVarEqual(1000000, "score1_value")
        self.assertMachineVarEqual('ABC', "score1_name")
        self.assertMachineVarEqual('HIGH SCORE 1', "score2_label")
        self.assertMachineVarEqual(900000, "score2_value")
        self.assertMachineVarEqual('ABC', "score2_name")
        self.assertMachineVarEqual('HIGH SCORE 2', "score3_label")
        self.assertMachineVarEqual(800000, "score3_value")
        self.assertMachineVarEqual('ABC', "score3_name")
        self.assertMachineVarEqual('HIGH SCORE 3', "score4_label")
        self.assertMachineVarEqual(700000, "score4_value")
        self.assertMachineVarEqual('ABC', "score4_name")
        self.assertMachineVarEqual('HIGH SCORE 4', "score5_label")
        self.assertMachineVarEqual(600000, "score5_value")
        self.assertMachineVarEqual('ABC', "score5_name")
        self.assertMachineVarEqual('LOOP CHAMP', "loops1_label")
        self.assertMachineVarEqual(500000, "loops1_value")
        self.assertMachineVarEqual('MPF', "loops1_name")

        self.assertModeNotRunning("high_score")

        self.post_event("high_scores_reset")
        self.advance_time_and_run(.1)

        new_score_data = dict()
        new_score_data['score'] = [['BRI', 4242],
                                   ['GHK', 2323],
                                   ['JK', 1337],
                                   ['QC', 42],
                                   ['MPF', 23]]
        new_score_data['loops'] = [['JK', 42]]

        self.assertEqual(new_score_data, self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

        self.assertMachineVarEqual('GRAND CHAMPION', "score1_label")
        self.assertMachineVarEqual(4242, "score1_value")
        self.assertMachineVarEqual('BRI', "score1_name")
        self.assertMachineVarEqual('HIGH SCORE 1', "score2_label")
        self.assertMachineVarEqual(2323, "score2_value")
        self.assertMachineVarEqual('GHK', "score2_name")
        self.assertMachineVarEqual('HIGH SCORE 2', "score3_label")
        self.assertMachineVarEqual(1337, "score3_value")
        self.assertMachineVarEqual('JK', "score3_name")
        self.assertMachineVarEqual('HIGH SCORE 3', "score4_label")
        self.assertMachineVarEqual(42, "score4_value")
        self.assertMachineVarEqual('QC', "score4_name")
        self.assertMachineVarEqual('HIGH SCORE 4', "score5_label")
        self.assertMachineVarEqual(23, "score5_value")
        self.assertMachineVarEqual('MPF', "score5_name")
        self.assertMachineVarEqual('LOOP CHAMP', "loops1_label")
        self.assertMachineVarEqual(42, "loops1_value")
        self.assertMachineVarEqual('JK', "loops1_name")

        self.mock_event("high_score_enter_initials")
        self.start_game()
        self.advance_time_and_run()
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)
        self.assertEqual(1, self._events['high_score_enter_initials'])
        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))

        self.advance_time_and_run(5)

        self.assertMachineVarEqual('GRAND CHAMPION', "score1_label")
        self.assertMachineVarEqual(8000000, "score1_value")
        self.assertMachineVarEqual('NEW', "score1_name")
        self.assertMachineVarEqual('HIGH SCORE 1', "score2_label")
        self.assertMachineVarEqual(4242, "score2_value")
        self.assertMachineVarEqual('BRI', "score2_name")
        self.assertMachineVarEqual('HIGH SCORE 2', "score3_label")
        self.assertMachineVarEqual(2323, "score3_value")
        self.assertMachineVarEqual('GHK', "score3_name")
        self.assertMachineVarEqual('HIGH SCORE 3', "score4_label")
        self.assertMachineVarEqual(1337, "score4_value")
        self.assertMachineVarEqual('JK', "score4_name")
        self.assertMachineVarEqual('HIGH SCORE 4', "score5_label")
        self.assertMachineVarEqual(42, "score5_value")
        self.assertMachineVarEqual('QC', "score5_name")
        self.assertMachineVarEqual('LOOP CHAMP', "loops1_label")
        self.assertMachineVarEqual(42, "loops1_value")
        self.assertMachineVarEqual('JK', "loops1_name")

        # test reset after a game
        self.post_event("high_scores_reset")
        self.advance_time_and_run(.1)

        self.assertMachineVarEqual('GRAND CHAMPION', "score1_label")
        self.assertMachineVarEqual(4242, "score1_value")
        self.assertMachineVarEqual('BRI', "score1_name")
        self.assertMachineVarEqual('HIGH SCORE 1', "score2_label")
        self.assertMachineVarEqual(2323, "score2_value")
        self.assertMachineVarEqual('GHK', "score2_name")
        self.assertMachineVarEqual('HIGH SCORE 2', "score3_label")
        self.assertMachineVarEqual(1337, "score3_value")
        self.assertMachineVarEqual('JK', "score3_name")
        self.assertMachineVarEqual('HIGH SCORE 3', "score4_label")
        self.assertMachineVarEqual(42, "score4_value")
        self.assertMachineVarEqual('QC', "score4_name")
        self.assertMachineVarEqual('HIGH SCORE 4', "score5_label")
        self.assertMachineVarEqual(23, "score5_value")
        self.assertMachineVarEqual('MPF', "score5_name")
        self.assertMachineVarEqual('LOOP CHAMP', "loops1_label")
        self.assertMachineVarEqual(42, "loops1_value")
        self.assertMachineVarEqual('JK', "loops1_name")

        self.assertEqual(new_score_data, self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_add_player_during_high_score(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 1000]])

        self.start_game()
        self.advance_time_and_run()
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        self.assertEqual(1, self._events['high_score_enter_initials'])
        self.machine.game.request_player_add()
        self.advance_time_and_run()

        # player should not be added
        self.assertEqual(len(self.machine.game.player_list), 1)

    def test_1_high_score(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 1000]])

        self.start_game(4)
        self.advance_time_and_run()
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 1000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))

        # award slide display time is 4 secs
        self.advance_time_and_run(2)

        # make sure the high score mode is still running
        self.assertTrue(self.machine.modes["high_score"].active)

        # another 2 secs and it should be done
        self.advance_time_and_run(3)
        self.assertFalse(self.machine.modes["high_score"].active)

        new_score_data = dict()
        new_score_data['score'] = [['NEW', 8000000],
                                   ['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890],
                                   ['QC', 87890]]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)

        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_2_high_scores(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 1000]])

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 10000000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self._bcp_client.send.reset_mock()
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        # GC

        self.assertEqual(1, self._events['high_score_enter_initials'])
        self._bcp_client.send.reset_mock()

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))
        self.advance_time_and_run(1)

        # High score 1

        # award slide is 4 secs, but we only advanced 1, so the next request
        # should not have been sent yet
        self.assertEqual(1, self._events['high_score_enter_initials'])

        # advance 4 secs and it should be sent
        self.advance_time_and_run(4)
        self.assertEqual(2, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='P2')))
        self.advance_time_and_run(5)

        # High score done

        self.assertFalse(self.machine.modes["high_score"].active)

        # verify the data is accurate
        new_score_data = dict()
        new_score_data['score'] = [['NEW', 10000000],
                                   ['P2', 8000000],
                                   ['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890]]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_2_high_scores_and_timeout(self):
        self.mock_event("high_score_enter_initials")
        self.mock_event("high_score_award_display")
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 1000]])

        self.start_game(2)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 10000000
        self._bcp_client.send.reset_mock()
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        # GC
        self.assertEventCalledWith('high_score_enter_initials', award='GRAND CHAMPION', player_num=2, value=10000000)
        self.mock_event("high_score_enter_initials")
        # wait for timeout
        self.advance_time_and_run(20)
        self.assertEventNotCalled("high_score_award_display")

        # Player 2 did not react. Player 1 will be GC
        # no further slide in between
        self.assertEventCalledWith('high_score_enter_initials', award='GRAND CHAMPION', player_num=1, value=8000000)

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='P2')))
        self.advance_time_and_run(.5)
        self.assertEventCalledWith("high_score_award_display",
                                   award='GRAND CHAMPION', player_name='P2', value=8000000)
        self.mock_event("high_score_award_display")
        self.advance_time_and_run(4)

        # High score done

        self.assertFalse(self.machine.modes["high_score"].active)

        # verify the data is accurate
        new_score_data = dict()
        new_score_data['score'] = [['P2', 8000000],
                                   ['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890],
                                   ['QC', 87890]]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_new_score_to_incomplete_list(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['MPF', 1000]])

        self.start_game(4)
        self.machine.game.player_list[0].score = 1500
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))

        self.advance_time_and_run(5)
        self.assertFalse(self.machine.modes["high_score"].active)

        new_score_data = dict()
        new_score_data['score'] = [['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['NEW', 1500],
                                   ['MPF', 1000]]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_more_than_3_chars(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 1000]])

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 1000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete',
                                                                   text='NEWNEW')))

        self.advance_time_and_run(5)
        self.assertFalse(self.machine.modes["high_score"].active)

        new_score_data = dict()
        new_score_data['score'] = [['NEWNEW', 8000000],
                                   ['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890],
                                   ['QC', 87890]]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_multiple_awards(self):
        self.mock_event("high_score_enter_initials")
        self.mock_event("high_score_award_display")
        # tests multiple awards (score & loops)
        # also tests 2 players getting an award for one slot, so only the
        # highest one should be presented
        # also tests the order (score first, then loops)
        self.machine.modes["high_score"].high_scores = dict()
        self.machine.modes["high_score"].high_scores['score'] = [['BRI', 7050550],
                                                              ['GHK', 93060],
                                                              ['JK', 87890],
                                                              ['QC', 87890],
                                                              ['MPF', 1000]]
        self.machine.modes["high_score"].high_scores['loops'] = [['BIL', 2]]

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 10000000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.player_list[0].loops = 50
        self.machine.game.player_list[1].loops = 4
        self.machine.game.player_list[2].loops = 1
        self.machine.game.player_list[3].loops = 0
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        # GC

        self.assertEqual(1, self._events['high_score_enter_initials'])
        self._bcp_client.send.reset_mock()

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))
        self.advance_time_and_run(.5)
        self.assertEventCalledWith("high_score_award_display",
                                   award='GRAND CHAMPION', player_name='NEW', value=10000000)
        self.mock_event("high_score_award_display")
        self.advance_time_and_run(4)

        # High score 1

        self.assertEqual(2, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='P1')))
        self.advance_time_and_run(.5)
        self.assertEventCalledWith("high_score_award_display",
                                   award='HIGH SCORE 1', player_name='P1', value=8000000)
        self.mock_event("high_score_award_display")
        self.advance_time_and_run(4)

        # Loops champ should not ask again but show a slide
        self.assertTrue(self.machine.modes["high_score"].active)
        self.advance_time_and_run(.5)
        self.assertEventCalledWith("high_score_award_display",
                                   award='LOOP CHAMP', player_name='P1', value=50)
        self.mock_event("high_score_award_display")
        self.advance_time_and_run(4)

        # High score done
        self.assertFalse(self.machine.modes["high_score"].active)

        # verify the data is accurate

        new_score_data = dict()
        new_score_data['score'] = [['NEW', 10000000],
                                   ['P1', 8000000],
                                   ['BRI', 7050550],
                                   ['GHK', 93060],
                                   ['JK', 87890]]
        new_score_data['loops'] = [['P1', 50]]

        # only ask every player once
        self.assertEqual(2, self._events['high_score_enter_initials'])

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_score_from_nonexistent_player_var(self):
        self.machine.modes["high_score"].high_scores = dict(
            score=[['BRI', 7050550],
                   ['GHK', 93060],
                   ['JK', 87890],
                   ['QC', 87890],
                   ['MPF', 1000]])

        self.start_game(4)
        self.machine.game.end_game()
        self.advance_time_and_run()

        self.assertFalse(self.machine.modes["high_score"].active)

        new_score_data = dict()
        new_score_data['score'] = [['BRI', 7050550],
                                    ['GHK', 93060],
                                    ['JK', 87890],
                                    ['QC', 87890],
                                    ['MPF', 1000]]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def _get_mock_data(self):
        if self._testMethodName == "testInvalidData":
            new_score_data = dict()
            new_score_data['score'] = [[13, '123'],
                                       [123.1, 4],
                                       [1]]
            new_score_data['loops'] = ""

            return {"high_scores": new_score_data}
        elif self._testMethodName == "testLoadData":
            new_score_data = dict()
            new_score_data['score'] = [['BRI', 5],
                                       ['GHK', 4],
                                       ['JK', 3],
                                       ['QC', 2],
                                       ['MPF', 1]]
            new_score_data['loops'] = [['MPF', 7]]
            return {"high_scores": new_score_data}
        elif self._testMethodName == "test_reset":
            new_score_data = dict(
                score=[['ABC', 1000000],
                       ['ABC', 900000],
                       ['ABC', 800000],
                       ['ABC', 700000],
                       ['ABC', 600000]],
                loops=[['MPF', 500000]])
            return {"high_scores": new_score_data}

        return super()._get_mock_data()

    def testLoadData(self):
        new_score_data = dict()
        new_score_data['score'] = [['BRI', 5],
                                   ['GHK', 4],
                                   ['JK', 3],
                                   ['QC', 2],
                                   ['MPF', 1]]
        new_score_data['loops'] = [['MPF', 7]]
        self.assertEqual(new_score_data, self.machine.modes["high_score"].high_scores)
        # no changes yet
        self.assertEqual(None, self.machine.modes["high_score"].data_manager.written_data)

    def testInvalidData(self):
        self.start_game(4)
        self.machine.game.game_ending()
        self.advance_time_and_run(10)

        # this should reload the defaults
        new_score_data = dict()
        new_score_data['score'] = [['BRI', 4242],
                                   ['GHK', 2323],
                                   ['JK', 1337],
                                   ['QC', 42],
                                   ['MPF', 23]]
        new_score_data['loops'] = [['JK', 42]]

        self.assertEqual(new_score_data, self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    @test_config_directory("tests/machine_files/high_score_reverse/")
    def test_reverse_sort(self):
        self.start_game(4)
        self.machine.game.game_ending()
        self.advance_time_and_run()

        new_score_data = dict()
        new_score_data['score'] = [['BRI', 4242],
                                   ['GHK', 2323],
                                   ['JK', 1337],
                                   ['QC', 42],
                                   ['MPF', 23]]
        new_score_data['loops'] = [['JK', 42]]
        new_score_data['time_to_wizard'] = [['JK', 300],
                                            ['BM', 350]]
        self.assertEqual(new_score_data, self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)
