from collections import OrderedDict

from mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.data_manager import DataManager


class TestHighScoreMode(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']

        # path DataManager so it doesn't actually write anything to disk
        DataManager._make_sure_path_exists = MagicMock()
        DataManager.save_all = MagicMock()

    def getConfigFile(self):
        return 'high_score.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/high_score/'

    def start_game(self, num_players=1):

        self.patch_bcp()

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

        bcp_command = ('trigger', None, {'value': 8000000, 'player_num': 1,
                                         'award': 'GRAND CHAMPION',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='NEW'), None))

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
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        # GC

        bcp_command = ('trigger', None, {'value': 10000000, 'player_num': 2,
                                         'award': 'GRAND CHAMPION',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)
        self.sent_bcp_commands = list()

        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='NEW'), None))
        self.advance_time_and_run(1)

        # High score 1

        bcp_command = ('trigger', None, {'value': 8000000, 'player_num': 1,
                                         'award': 'HIGH SCORE 1',
                                         'name': 'new_high_score'})

        # award slide is 4 secs, but we only advanced 1, so the next request
        # should not have been sent yet

        self.assertNotIn(bcp_command, self.sent_bcp_commands)

        # advance 4 secs and it should be sent
        self.advance_time_and_run(4)
        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='P2'), None))
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
        self.machine.modes.high_score.high_scores = OrderedDict(
            score=[('BRI', 7050550),
                   ('GHK', 93060),
                   ('MPF', 1000)])

        self.start_game(4)
        self.machine.game.player_list[0].score = 1500
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        bcp_command = ('trigger', None, {'value': 1500, 'player_num': 1,
                                         'award': 'HIGH SCORE 2',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='NEW'), None))

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

        bcp_command = ('trigger', None, {'value': 8000000, 'player_num': 1,
                                         'award': 'GRAND CHAMPION',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='NEWNEW'), None))

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

        bcp_command = ('trigger', None, {'value': 10000000, 'player_num': 2,
                                         'award': 'GRAND CHAMPION',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)
        self.sent_bcp_commands = list()
        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='NEW'), None))
        self.advance_time_and_run(5)

        # High score 1

        bcp_command = ('trigger', None, {'value': 8000000, 'player_num': 1,
                                         'award': 'HIGH SCORE 1',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)
        self.sent_bcp_commands = list()
        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='P1'), None))
        self.advance_time_and_run(5)

        # Loops champ

        bcp_command = ('trigger', None, {'value': 50, 'player_num': 1,
                                         'award': 'LOOP CHAMP',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)
        self.sent_bcp_commands = list()
        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='YAY'), None))
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
