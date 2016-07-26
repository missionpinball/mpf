"""Test the bonus mode."""
from mpf.tests.MpfTestCase import MpfTestCase


class TestMachineVariables(MpfTestCase):

    def _get_mock_data(self):
        return {"machine_vars": {"player2_score": {"value": 118208660},
                                 "player3_score": {"value": 17789290},
                                 "player4_score": {"value": 3006600},
                                 "another_score": {"value": 123}},
                }

    def testVarLoadAndRemove(self):
        self.assertTrue(self.machine.is_machine_var("player2_score"))
        self.assertEqual(118208660, self.machine.get_machine_var("player2_score"))

        self.machine.remove_machine_var("player2_score")

        self.assertFalse(self.machine.is_machine_var("player2_score"))
        self.assertTrue(self.machine.is_machine_var("player3_score"))

        self.machine.remove_machine_var_search(startswith="player", endswith="_score")
        self.assertFalse(self.machine.is_machine_var("player2_score"))
        self.assertFalse(self.machine.is_machine_var("player3_score"))

        self.assertEqual(123, self.machine.get_machine_var("another_score"))


class TestMalformedMachineVariables(MpfTestCase):

    def _get_mock_data(self):
        return {"machine_vars": {"player2_score": {"value": 118208660},
                                 "player3_score": {"value": 17789290},
                                 "player4_score": {"value": 3006600},
                                 "player5_score": 123,
                                 "player6_score": {"asd": 3006600},
                                 "value": 0}}

    def testVarLoads(self):
        self.assertTrue(self.machine.is_machine_var("player2_score"))
        self.assertEqual(118208660, self.machine.get_machine_var("player2_score"))
        self.assertFalse(self.machine.is_machine_var("player5_score"))
        self.assertEqual(None, self.machine.get_machine_var("player5_score"))
