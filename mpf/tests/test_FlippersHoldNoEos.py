from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock, call


class TestFlippers(MpfTestCase):

    def getConfigFile(self):
        return 'hold_no_eos.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/flippers/'

    def get_platform(self):
        return 'virtual'

    def test_hold_no_eos(self):
        self.machine.default_platform.set_pulse_on_hit_and_release_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        # Config uses enable_events to enable the flipper on boot
        self.assertTrue(self.machine.flippers.left_flipper._enabled)
        self.machine.flippers.left_flipper.disable()

        self.assertFalse(self.machine.flippers.left_flipper._enabled)
        self.machine.flippers.left_flipper.enable()
        #     def set_hw_rule(self, sw_name, sw_activity, driver_name, driver_action,
        #                     disable_on_release=True, drive_now=False,
        #                     **driver_settings_overrides):
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_release_rule._mock_call_args_list))
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
        # TODO: check parameter for rule main pulse
        # TODO: check parameter for rule hold pwm

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.left_flipper.disable()
        self.assertFalse(self.machine.flippers.left_flipper._enabled)

        self.machine.default_platform.clear_hw_rule.assert_has_calls(
            [call(self.machine.flippers.left_flipper.switch.get_configured_switch(),
                  self.machine.flippers.left_flipper.main_coil.get_configured_driver()),
             call(self.machine.flippers.left_flipper.switch.get_configured_switch(),
                  self.machine.flippers.left_flipper.hold_coil.get_configured_driver())]
        )

        self.machine.default_platform.set_pulse_on_hit_and_release_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()
        self.machine.flippers.left_flipper.enable()
        self.assertTrue(self.machine.flippers.left_flipper._enabled)
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_release_rule._mock_call_args_list))
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
