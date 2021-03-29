"""Test digital score reels."""

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase

class TestDigitalScoreReels(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'test_digital_score_reels.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/digital_score_reels'

    def test_player_score(self):
        self.mock_event('score_reel_player_score_player1')
        self.mock_event('score_reel_player_score_player2')
        self.start_two_player_game()
        self.assertGameIsRunning()

        self.assertPlayerNumber(1)
        self.advance_time_and_run()
        self.machine.game.player.score = 123
        self.advance_time_and_run()
        self.assertEqual({"1": "20", "2": "2", "3": "4", "4": "6"}, self._last_event_kwargs['score_reel_player_score_player1'])
        self.assertEventNotCalled('score_reel_player_score_player2')

        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.machine.game.player.score = 9876
        self.advance_time_and_run()
        self.assertEqual({"1": "18", "2": "16", "3": "14", "4": "12"}, self._last_event_kwargs['score_reel_player_score_player2'])

    def test_arbitrary_event(self):
        self.mock_event('score_reel_arbitrary_event')
        self.post_event_with_params('arbitrary_event', value='AB')
        self.advance_time_and_run()
        self.assertEqual({"1": "6", "2": "1", "3": "2"}, self._last_event_kwargs['score_reel_arbitrary_event'])

        self.post_event_with_params('arbitrary_event', value='DXB')
        self.advance_time_and_run()
        self.assertEqual({"1": "4", "2":"6", "3": "2"}, self._last_event_kwargs['score_reel_arbitrary_event'])

        self.post_event_with_params('arbitrary_event', value='EC')
        self.advance_time_and_run()
        self.assertEqual({"1": "6", "2":"5", "3": "3"}, self._last_event_kwargs['score_reel_arbitrary_event'])