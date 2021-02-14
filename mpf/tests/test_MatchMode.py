from unittest.mock import patch

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import test_config


class TestMatchMode(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/match_mode/'

    def get_platform(self):
        return 'smart_virtual'

    @test_config("config_highscore.yaml")
    def test_service_during_high_score(self):
        """Regression test for crash when service started during high score and cancels match."""
        self.post_event("add_credit")
        self.start_game()

        self.machine.game.player_list[0].score = 8000000
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.drain_one_ball()
        self.advance_time_and_run(1)
        self.post_event("sw_service_enter_active")
        self.advance_time_and_run(1)

    def test_no_match(self):
        self.post_event("add_credit")
        self.assertMachineVarEqual(1, "credits_whole_num")

        self.start_game()
        self.assertMachineVarEqual(0, "credits_whole_num")

        self.machine.game.player.score += 1337

        self.mock_event("match_no_match")
        self.mock_event("match_has_match")

        with patch("mpf.modes.match.code.match.random.randint") as randint:
            randint.return_value = 50
            self.drain_all_balls()
            self.advance_time_and_run()
        self.assertGameIsNotRunning()
        self.assertEventCalled("match_no_match")
        self.assertEventNotCalled("match_has_match")

        self.assertMachineVarEqual(0, "credits_whole_num")

    def test_match(self):
        self.post_event("add_credit")
        self.assertMachineVarEqual(1, "credits_whole_num")

        self.start_game()
        self.assertMachineVarEqual(0, "credits_whole_num")

        self.machine.game.player.score += 1337

        self.mock_event("match_no_match")
        self.mock_event("match_has_match")

        with patch("mpf.modes.match.code.match.random.randint") as randint:
            randint.return_value = 5
            self.drain_all_balls()
            self.advance_time_and_run()
        self.assertGameIsNotRunning()
        self.assertEventNotCalled("match_no_match")
        self.assertEventCalled("match_has_match")

        self.assertMachineVarEqual(1, "credits_whole_num")
