"""Test the bonus mode."""
from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase
from mpf._version import version, extended_version


class TestMachineVariables(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/machine_vars/'

    def _get_mock_data(self):
        return {"machine_vars": {"player2_score": {"value": 118208660},
                                 "player3_score": {"value": 17789290},
                                 "player4_score": {"value": 3006600},
                                 "another_score": {"value": 123},
                                 "expired_value": {"value": 23, "expire": self.clock.get_time() - 100},
                                 "not_expired_value": {"value": 24, "expire": self.clock.get_time() + 100},
                                 "test1": {"value": 42}},
                }

    def testSystemInfoVariables(self):
        self.assertTrue(self.machine.is_machine_var("mpf_version"))
        self.assertTrue(self.machine.is_machine_var("mpf_extended_version"))
        self.assertTrue(self.machine.is_machine_var("python_version"))
        self.assertTrue(self.machine.is_machine_var("platform"))
        self.assertTrue(self.machine.is_machine_var("platform_system"))
        self.assertTrue(self.machine.is_machine_var("platform_release"))
        self.assertTrue(self.machine.is_machine_var("platform_version"))
        self.assertTrue(self.machine.is_machine_var("platform_machine"))
        self.assertEqual(version, self.machine.get_machine_var("mpf_version"))
        self.assertEqual(extended_version, self.machine.get_machine_var("mpf_extended_version"))

    def testVarLoadAndRemove(self):
        self.assertFalse(self.machine.is_machine_var("expired_value"))
        self.assertTrue(self.machine.is_machine_var("not_expired_value"))
        self.assertTrue(self.machine.is_machine_var("player2_score"))
        # should always persist
        #self.assertTrue(self.machine.machine_vars["player2_score"]["persist"])
        # random variable does not persist
        self.assertFalse(self.machine.machine_vars["another_score"]["persist"])
        # configured to persist
        self.assertTrue(self.machine.machine_vars["test1"]["persist"])
        self.assertTrue(self.machine.machine_vars["test2"]["persist"])
        # configured to not persist
        self.assertFalse(self.machine.machine_vars["test3"]["persist"])
        self.assertEqual(118208660, self.machine.get_machine_var("player2_score"))

        self.machine.remove_machine_var("player2_score")

        self.assertFalse(self.machine.is_machine_var("player2_score"))
        self.assertTrue(self.machine.is_machine_var("player3_score"))

        self.machine.machine_var_data_manager._trigger_save = MagicMock()
        self.machine.remove_machine_var_search(startswith="player", endswith="_score")
        self.assertFalse(self.machine.is_machine_var("player2_score"))
        self.assertFalse(self.machine.is_machine_var("player3_score"))

        self.assertEqual(123, self.machine.get_machine_var("another_score"))

        self.advance_time_and_run(10)

        self.machine.machine_var_data_manager._trigger_save.assert_called_with()
        self.assertEqual({'test1': {'value': 42, 'expire': None}, 'test2': {'value': '5', 'expire': None}},
                         self.machine.machine_var_data_manager.data)


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
