"""Test the bonus mode."""
from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase
from mpf._version import version, extended_version


class TestMachineVariables(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/machine_vars/'

    def _get_mock_data(self):
        return {"machine_vars": {"player2_score": {"value": 118208660, 'expire': None, 'expire_secs': None},
                                 "player3_score": {"value": 17789290, 'expire': None, 'expire_secs': None},
                                 "player4_score": {"value": 3006600, 'expire': None, 'expire_secs': None},
                                 "another_score": {"value": 123, 'expire': None, 'expire_secs': None},
                                 "expired_value": {"value": 23,
                                                   "expire": self.clock.get_datetime().timestamp() - 100,
                                                   'expire_secs': 3600},
                                 "not_expired_value": {"value": 24,
                                                       "expire": self.clock.get_datetime().timestamp() + 100,
                                                       'expire_secs': 3600},
                                 "test1": {"value": 42, 'expire': None, 'expire_secs': None}},
                }

    def testSystemInfoVariables(self):
        self.assertTrue(self.machine.variables.is_machine_var("mpf_version"))
        self.assertTrue(self.machine.variables.is_machine_var("mpf_extended_version"))
        self.assertTrue(self.machine.variables.is_machine_var("python_version"))
        self.assertTrue(self.machine.variables.is_machine_var("platform"))
        self.assertTrue(self.machine.variables.is_machine_var("platform_system"))
        self.assertTrue(self.machine.variables.is_machine_var("platform_release"))
        self.assertTrue(self.machine.variables.is_machine_var("platform_version"))
        self.assertTrue(self.machine.variables.is_machine_var("platform_machine"))
        self.assertEqual(version, self.machine.variables.get_machine_var("mpf_version"))
        self.assertEqual(extended_version, self.machine.variables.get_machine_var("mpf_extended_version"))
        self.assertEqual(0.5, self.machine.variables.get_machine_var("master_volume"))

    def testTime(self):
        current_date = self.machine.clock.get_datetime()
        self.assertPlaceholderEvaluates(current_date.second, "machine.time.second")
        self.assertPlaceholderEvaluates(current_date.minute, "machine.time.minute")
        self.assertPlaceholderEvaluates(current_date.hour, "machine.time.hour")
        self.assertPlaceholderEvaluates(current_date.day, "machine.time.day")
        self.assertPlaceholderEvaluates(current_date.month, "machine.time.month")
        self.assertPlaceholderEvaluates(current_date.year, "machine.time.year")

        placeholder = self.machine.placeholder_manager.build_int_template("machine.time.second")
        value, future = placeholder.evaluate_and_subscribe({})
        self.assertEqual(current_date.second, value)
        self.assertFalse(future.done())

        self.advance_time_and_run(1.1)
        self.assertTrue(future.done())

        self.mock_event("test_event3")
        self.mock_event("test_event4")
        self.advance_time_and_run(60)
        self.assertEventCalled("test_event3", 1)
        self.assertEventCalled("test_event4", 1)
        self.advance_time_and_run(60)
        self.assertEventCalled("test_event3", 2)
        self.assertEventCalled("test_event4", 2)

    def testVarLoadAndRemove(self):
        self.assertFalse(self.machine.variables.is_machine_var("expired_value"))
        self.assertTrue(self.machine.variables.is_machine_var("not_expired_value"))
        self.assertTrue(self.machine.variables.is_machine_var("player2_score"))
        # previously-persisted variables should continue to persist
        self.assertTrue(self.machine.variables.machine_vars["player2_score"]["persist"])
        # random variable does not persist
        self.machine.variables.set_machine_var("temporary_variable", 1000)
        self.assertEqual(1000, self.machine.variables.get_machine_var("temporary_variable"))
        self.assertFalse(self.machine.variables.machine_vars["temporary_variable"]["persist"])
        # configured to persist
        self.assertTrue(self.machine.variables.machine_vars["test1"]["persist"])
        self.assertTrue(self.machine.variables.machine_vars["test2"]["persist"])
        # configured to not persist
        self.assertFalse(self.machine.variables.machine_vars["test3"]["persist"])
        self.assertEqual(118208660, self.machine.variables.get_machine_var("player2_score"))

        self.machine.variables.remove_machine_var("player2_score")

        self.assertFalse(self.machine.variables.is_machine_var("player2_score"))
        self.assertTrue(self.machine.variables.is_machine_var("player3_score"))

        self.machine.variables.machine_var_data_manager._trigger_save = MagicMock()
        self.machine.variables.remove_machine_var_search(startswith="player", endswith="_score")
        self.assertFalse(self.machine.variables.is_machine_var("player2_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))

        self.assertEqual(123, self.machine.variables.get_machine_var("another_score"))

        self.machine.variables.configure_machine_var("test3", expire_secs=100, persist=True)
        self.machine.variables.set_machine_var("test3", "Hello")
        ts = self.machine.clock.get_datetime().timestamp()

        self.advance_time_and_run(10)

        self.machine.variables.machine_var_data_manager._trigger_save.assert_called_with()
        self.assertEqual({
                          'another_score': {'value': 123, 'expire': None, 'expire_secs': None},
                          "not_expired_value": {'value': 24, 'expire': None, 'expire_secs': None},
                          'master_volume': {'value': 0.5, 'expire': None, 'expire_secs': None},
                          'test1': {'value': 42, 'expire': None, 'expire_secs': None},
                          'test2': {'value': '5', 'expire': None, 'expire_secs': None},
                          'test3': {'expire': ts + 100, 'expire_secs': 100, 'value': 'Hello'}},
                         self.machine.variables.machine_var_data_manager.data)

    def testVarSetAndGet(self):
        self.assertEqual(118208660, self.machine.variables["player2_score"])

        self.assertEqual(None, self.machine.variables["player1_score"])
        self.machine.variables["player1_score"] = 123
        self.assertEqual(123, self.machine.variables["player1_score"])

        self.assertEqual(17789290, self.machine.variables.get("player3_score"))


class TestMalformedMachineVariables(MpfTestCase):

    def _get_mock_data(self):
        return {"machine_vars": {"player2_score": {"value": 118208660, 'expire': None, 'expire_secs': None},
                                 "player3_score": {"value": 17789290, 'expire': None, 'expire_secs': None},
                                 "player4_score": {"value": 3006600},
                                 "player5_score": 123,
                                 "player6_score": {"asd": 3006600, 'expire': None, 'expire_secs': None},
                                 "value": 0}}

    def testVarLoads(self):
        self.assertTrue(self.machine.variables.is_machine_var("player2_score"))
        self.assertEqual(118208660, self.machine.variables.get_machine_var("player2_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player5_score"))
        self.assertEqual(None, self.machine.variables.get_machine_var("player5_score"))

