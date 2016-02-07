import unittest

from mpf.core.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock, call
import time

class TestTilt(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/flippers/'

    def get_platform(self):
        return 'virtual'

    def test_single(self):
        self.machine.default_platform.write_hw_rule = MagicMock()

        self.machine.flippers.f_test_single.enable()
        self.assertEqual(1, self.machine.default_platform.write_hw_rule.called)
        # TODO: check parameter for rule main pulse

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_single.disable()

        self.assertEqual(1, self.machine.default_platform.clear_hw_rule.called)
        self.machine.default_platform.clear_hw_rule.assert_called_once_with("s_flipper")

    def test_hold_no_eos(self):
        self.machine.default_platform.set_hw_rule = MagicMock()

        self.machine.flippers.f_test_hold.enable()
        #     def set_hw_rule(self, sw_name, sw_activity, driver_name, driver_action,
        #                     disable_on_release=True, drive_now=False,
        #                     **driver_settings_overrides):
        self.assertEqual(2, len(self.machine.default_platform.set_hw_rule._mock_call_args_list))
        # TODO: check parameter for rule main pulse
        # TODO: check parameter for rule hold pwm

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_hold.disable()

        self.assertEqual(1, self.machine.default_platform.clear_hw_rule.called)
        self.machine.default_platform.clear_hw_rule.assert_called_once_with("s_flipper")

    def test_hold_with_eos(self):
        self.machine.default_platform.set_hw_rule = MagicMock()

        self.machine.flippers.f_test_hold_eos.enable()
        self.assertEqual(2, len(self.machine.default_platform.set_hw_rule._mock_call_args_list))
        # TODO: check parameter for rule main enable
        # TODO: check parameter for rule hold pwm

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_hold_eos.disable()

        self.assertEqual(1, len(self.machine.default_platform.clear_hw_rule._mock_call_args_list))
        self.machine.default_platform.clear_hw_rule.assert_has_calls([call("s_flipper")])
        # TODO: this should be clear_hw_rule on s_flipper and s_flipper_eos
        #self.assertEqual(2, len(self.machine.default_platform.clear_hw_rule._mock_call_args_list))
        #self.machine.default_platform.clear_hw_rule.assert_has_calls([call("s_flipper"), call("s_flipper_eos")])

    def test_sw_flip_and_release(self):

        self.machine.coils.c_flipper_main.enable = MagicMock()
        self.machine.coils.c_flipper_main.disable = MagicMock()
        self.machine.flippers.f_test_hold_eos.sw_flip()
        self.machine.coils.c_flipper_main.enable.assert_called_once_with()

        self.machine.flippers.f_test_hold_eos.sw_release()
        self.machine.coils.c_flipper_main.disable.assert_called_once_with()
