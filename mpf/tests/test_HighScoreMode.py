"""Test high score mode."""
from collections import OrderedDict

from unittest.mock import MagicMock, call
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase


class TestHighScoreMode(MpfBcpTestCase):

    def getConfigFile(self):
        return 'high_score.yaml'

    def getMachinePath(self):
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

    def test_no_high_scores(self):
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('JK', 87890),
                   ('QC', 87890),
                   ('MPF', 10000)])

        self.start_game(4)
        self.machine.game.player_list[0].score = 1000
        self.machine.game.player_list[1].score = 1000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertFalse(self.machine.modes.high_score.active)

    def test_1_high_score(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('JK', 87890),
                   ('QC', 87890),
                   ('MPF', 1000)])

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 1000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))

        # award slide display time is 4 secs
        self.advance_time_and_run(2)

        # make sure the high score mode is still running
        self.assertTrue(self.machine.modes.high_score.active)

        # another 2 secs and it should be done
        self.advance_time_and_run(2)
        self.assertFalse(self.machine.modes.high_score.active)

        new_score_data = OrderedDict()
        new_score_data['score'] = [('NEW', 8000000),
                                   ('BRI', 7050550),
                                   ('GHK', 93060),
                                   ('JK', 87890),
                                   ('QC', 87890)]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)

    def test_2_high_scores(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('JK', 87890),
                   ('QC', 87890),
                   ('MPF', 1000)])

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 10000000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self._bcp_client.send.reset_mock()
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

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

        self.assertFalse(self.machine.modes.high_score.active)

        # verify the data is accurate
        new_score_data = OrderedDict()
        new_score_data['score'] = [('NEW', 10000000),
                                   ('P2', 8000000),
                                   ('BRI', 7050550),
                                   ('GHK', 93060),
                                   ('JK', 87890)]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)

    def test_new_score_to_incomplete_list(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('MPF', 1000)])

        self.start_game(4)
        self.machine.game.player_list[0].score = 1500
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))

        self.advance_time_and_run(5)
        self.assertFalse(self.machine.modes.high_score.active)

        new_score_data = OrderedDict()
        new_score_data['score'] = [('BRI', 7050550),
                                   ('GHK', 93060),
                                   ('NEW', 1500),
                                   ('MPF', 1000)]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)

    def test_more_than_3_chars(self):
        self.mock_event("high_score_enter_initials")
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('JK', 87890),
                   ('QC', 87890),
                   ('MPF', 1000)])

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 1000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        self.assertEqual(1, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete',
                                                                   text='NEWNEW')))

        self.advance_time_and_run(5)
        self.assertFalse(self.machine.modes.high_score.active)

        new_score_data = OrderedDict()
        new_score_data['score'] = [('NEWNEW', 8000000),
                                   ('BRI', 7050550),
                                   ('GHK', 93060),
                                   ('JK', 87890),
                                   ('QC', 87890)]
        new_score_data['loops'] = []

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)

    def test_multiple_awards(self):
        self.mock_event("high_score_enter_initials")
        # tests multiple awards (score & loops)
        # also tests 2 players getting an award for one slot, so only the
        # highest one should be presented
        # also tests the order (score first, then loops)
        self.machine.modes.high_score.high_scores = OrderedDict()
        self.machine.modes.high_score.high_scores['score'] = [('BRI', 7050550),
                                                              ('GHK', 93060),
                                                              ('JK', 87890),
                                                              ('QC', 87890),
                                                              ('MPF', 1000)]
        self.machine.modes.high_score.high_scores['loops'] = [('BIL', 2)]

        self.start_game(4)
        self.machine.game.player_list[0].score = 8000000
        self.machine.game.player_list[1].score = 10000000
        self.machine.game.player_list[2].score = 1000
        self.machine.game.player_list[3].score = 1000
        self.machine.game.player_list[0].loops = 50
        self.machine.game.player_list[1].loops = 4
        self.machine.game.player_list[2].loops = 1
        self.machine.game.player_list[3].loops = 0
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        # GC

        self.assertEqual(1, self._events['high_score_enter_initials'])
        self._bcp_client.send.reset_mock()

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))
        self.advance_time_and_run(5)

        # High score 1

        self.assertEqual(2, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='P1')))
        self.advance_time_and_run(5)

        # Loops champ

        self.assertEqual(3, self._events['high_score_enter_initials'])

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='YAY')))
        self.advance_time_and_run(5)

        # High score done

        self.assertFalse(self.machine.modes.high_score.active)

        # verify the data is accurate

        new_score_data = OrderedDict()
        new_score_data['score'] = [('NEW', 10000000),
                                   ('P1', 8000000),
                                   ('BRI', 7050550),
                                   ('GHK', 93060),
                                   ('JK', 87890)]
        new_score_data['loops'] = [('YAY', 50)]

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)

    def test_score_from_nonexistent_player_var(self):
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('JK', 87890),
                   ('QC', 87890),
                   ('MPF', 1000)])

        self.start_game(4)
        self.machine.game.game_ending()
        self.advance_time_and_run()

        self.assertFalse(self.machine.modes.high_score.active)

        new_score_data = OrderedDict()
        new_score_data['score'] = [('BRI', 7050550),
                                   ('GHK', 93060),
                                   ('JK', 87890),
                                   ('QC', 87890),
                                   ('MPF', 1000)]

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)
