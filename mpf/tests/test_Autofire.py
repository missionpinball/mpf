from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestAutofire(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/autofire/'

    def test_hw_rule_pulse(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofires.ac_test.enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            self.machine.autofires.ac_test.switch.get_configured_switch(),
            self.machine.autofires.ac_test.coil.get_configured_driver()
        )

        switch_config = self.machine.autofires.ac_test.switch.get_configured_switch()
        self.assertFalse(switch_config.invert)

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofires.ac_test.disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            self.machine.autofires.ac_test.switch, self.machine.autofires.ac_test.coil)

    def test_hw_rule_pulse_inverted_switch(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofires.ac_test_inverted.enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            self.machine.autofires.ac_test_inverted.switch.get_configured_switch(),
            self.machine.autofires.ac_test_inverted.coil.get_configured_driver()
        )

        switch_config = self.machine.autofires.ac_test_inverted.switch.get_configured_switch()
        self.assertTrue(switch_config.invert)

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofires.ac_test_inverted.disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            self.machine.autofires.ac_test_inverted.switch, self.machine.autofires.ac_test_inverted.coil)

    def test_hw_rule_pulse_inverted_autofire(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofires.ac_test_inverted2.enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            self.machine.autofires.ac_test_inverted2.switch.get_configured_switch(),
            self.machine.autofires.ac_test_inverted2.coil.get_configured_driver()
        )

        switch_config = self.machine.autofires.ac_test_inverted2.switch.get_configured_switch()
        self.assertTrue(switch_config.invert)

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofires.ac_test_inverted2.disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            self.machine.autofires.ac_test_inverted2.switch, self.machine.autofires.ac_test_inverted2.coil)
