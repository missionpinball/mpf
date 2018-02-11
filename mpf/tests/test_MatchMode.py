from unittest.mock import patch

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestMatchMode(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/match_mode/'

    def get_platform(self):
        return 'smart_virtual'

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
            self.drain_ball()
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
            self.drain_ball()
            self.advance_time_and_run()
        self.assertGameIsNotRunning()
        self.assertEventNotCalled("match_no_match")
        self.assertEventCalled("match_has_match")

        self.assertMachineVarEqual(1, "credits_whole_num")
