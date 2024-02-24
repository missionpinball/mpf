"""Test high score mode."""
from unittest.mock import MagicMock
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase


class TestHighScoreMode(MpfBcpTestCase):

    def get_config_file(self):
        return 'high_score.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/high_score_vars/'

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

    def test_high_score_one_var(self):
        self.advance_time_and_run()
        self.mock_event("high_score_enter_initials")
        self.mock_event("loops_award_display")
        # tests loop award with additional variables
        self.machine.modes["high_score"].high_scores = dict()
        self.machine.modes["high_score"].high_scores['loops'] = [('BIL', 2)]

        self.start_game(1)
        self.machine.game.player_list[0].loops = 50
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        # Award initials
        self.assertEqual(1, self._events['high_score_enter_initials'])
        self._bcp_client.send.reset_mock()

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))
        self.advance_time_and_run(.5)

        self.assertEventCalledWith("loops_award_display", award='LOOP CHAMP', player_name='NEW', value=50,
                                   player_num=1, category_name='loops')
        self.advance_time_and_run(4)

        # High score done
        self.assertFalse(self.machine.modes["high_score"].active)

        # verify the data is accurate

        new_score_data = {'score': [], 'loops': [['NEW', 50, {'player_number': 1}]], 'hits': []}

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)

    def test_high_score_multiple_vars(self):
        self.advance_time_and_run()
        self.mock_event("high_score_enter_initials")
        self.mock_event("hits_award_display")
        # tests loop award with additional variables
        self.machine.modes["high_score"].high_scores = dict()
        self.machine.modes["high_score"].high_scores['hits'] = [['AAA', 2]]

        self.start_game(1)
        self.machine.game.player_list[0].hits = 50
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes["high_score"].active)

        # Award initials
        self.assertEqual(1, self._events['high_score_enter_initials'])
        self._bcp_client.send.reset_mock()

        self._bcp_client.receive_queue.put_nowait(('trigger', dict(name='text_input_high_score_complete', text='NEW')))
        self.advance_time_and_run(.5)

        self.assertEventCalledWith("hits_award_display", award='MOST HITS', player_name='NEW', value=50,
                                   player_num=1, category_name='hits')
        self.advance_time_and_run(4)

        # High score done
        self.assertFalse(self.machine.modes["high_score"].active)

        # verify the data is accurate

        new_score_data = {'score': [],
                          'loops': [],
                          'hits': [['NEW', 50, {'player_number': 1, 'machine_credits_string': 'FREE PLAY'}]]}

        self.assertEqual(new_score_data,
                         self.machine.modes["high_score"].high_scores)
        self.assertEqual(new_score_data, self.machine.modes["high_score"].data_manager.written_data)
