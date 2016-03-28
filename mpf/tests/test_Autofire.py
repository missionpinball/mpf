from mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestAutofire(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/autofire/'

    def test_hw_rule_pulse(self):
        self.machine.default_platform.write_hw_rule = MagicMock()
        self.machine.autofires.ac_test.enable()

        self.assertEqual(
            (self.machine.autofires.ac_test.switch,
             1,
             self.machine.coils.c_test,
             'pulse',
             False,
             False), self.machine.default_platform.write_hw_rule._mock_call_args_list[0][0])

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofires.ac_test.disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with("s_test")

    def test_hw_rule_pulse_inverted_switch(self):
        self.machine.default_platform.write_hw_rule = MagicMock()
        self.machine.autofires.ac_test_inverted.enable()

        self.assertEqual(
            (self.machine.autofires.ac_test_inverted.switch,
             0,
             self.machine.coils.c_test2,
             'pulse',
             False,
             False), self.machine.default_platform.write_hw_rule._mock_call_args_list[0][0])

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofires.ac_test_inverted.disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with("s_test_nc")

    def test_hw_rule_pulse_inverted_autofire(self):
        self.machine.default_platform.write_hw_rule = MagicMock()
        self.machine.autofires.ac_test_inverted2.enable()

        self.assertEqual(
            (self.machine.autofires.ac_test_inverted2.switch,
             0,
             self.machine.coils.c_test2,
             'pulse',
             False,
             False), self.machine.default_platform.write_hw_rule._mock_call_args_list[0][0])

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofires.ac_test_inverted.disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with("s_test_nc")