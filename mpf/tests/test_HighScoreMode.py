from collections import OrderedDict

from mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase
import ruamel.yaml as yaml


class TestHighScoreMode(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']

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

        self.advance_time_and_run()
        self.assertFalse(self.machine.modes.high_score.active)

        new_score_data = OrderedDict(score=[('NEW', 8000000),
                                            ('BRI', 7050550),
                                            ('GHK', 93060),
                                            ('JK', 87890),
                                            ('QC', 87890)])

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
        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='NEW'), None))
        self.advance_time_and_run()

        # High score 1

        bcp_command = ('trigger', None, {'value': 8000000, 'player_num': 1,
                                         'award': 'HIGH SCORE 1',
                                         'name': 'new_high_score'})

        self.assertIn(bcp_command, self.sent_bcp_commands)
        self.machine.bcp.receive_queue.put(('trigger',
            dict(name='text_input_high_score_complete', text='P2'), None))
        self.advance_time_and_run()

        # High score done

        self.assertFalse(self.machine.modes.high_score.active)

        # verify the data is accurate

        new_score_data = OrderedDict(score=[('NEW', 10000000),
                                            ('P2', 8000000),
                                            ('BRI', 7050550),
                                            ('GHK', 93060),
                                            ('JK', 87890)])

        self.assertEqual(new_score_data,
                         self.machine.modes.high_score.high_scores)

    def test_new_score_to_incomplete_list(self):
        pass

    def test_multiple_awards(self):
        pass

    def test_award_slide_display_time(self):
        pass

    def test_timeout(self):
        pass
