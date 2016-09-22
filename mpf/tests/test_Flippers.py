from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock, call


class TestFlippers(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/flippers/'

    def get_platform(self):
        return 'virtual'

    def test_single(self):
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        self.machine.flippers.f_test_single.enable()
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
        self.assertEqual(
            (self.machine.flippers.f_test_single.switch.get_configured_switch(),
             self.machine.flippers.f_test_single.main_coil.get_configured_driver()),
            self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule._mock_call_args_list[0][0])

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_single.disable()

        self.assertEqual(1, self.machine.default_platform.clear_hw_rule.called)
        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            self.machine.flippers.f_test_single.switch.get_configured_switch(),
            self.machine.flippers.f_test_single.main_coil.get_configured_driver())

    def test_hold_no_eos(self):
        self.machine.default_platform.set_pulse_on_hit_and_release_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        self.assertFalse(self.machine.flippers.f_test_hold._enabled)
        self.machine.flippers.f_test_hold.enable()
        #     def set_hw_rule(self, sw_name, sw_activity, driver_name, driver_action,
        #                     disable_on_release=True, drive_now=False,
        #                     **driver_settings_overrides):
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_release_rule._mock_call_args_list))
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
        # TODO: check parameter for rule main pulse
        # TODO: check parameter for rule hold pwm

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_hold.disable()
        self.assertFalse(self.machine.flippers.f_test_hold._enabled)

        self.machine.default_platform.clear_hw_rule.assert_has_calls(
            [call(self.machine.flippers.f_test_hold.switch.get_configured_switch(),
                  self.machine.flippers.f_test_hold.main_coil.get_configured_driver()),
             call(self.machine.flippers.f_test_hold.switch.get_configured_switch(),
                  self.machine.flippers.f_test_hold.hold_coil.get_configured_driver())]
        )

        self.machine.default_platform.set_pulse_on_hit_and_release_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()
        self.machine.flippers.f_test_hold.enable()
        self.assertTrue(self.machine.flippers.f_test_hold._enabled)
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_release_rule._mock_call_args_list))
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))

    def test_hold_with_eos(self):
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        self.machine.flippers.f_test_hold_eos.enable()
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule
                                ._mock_call_args_list))
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_hold_eos.disable()

        self.machine.default_platform.clear_hw_rule.assert_has_calls(
            [call(self.machine.flippers.f_test_hold_eos.switch, self.machine.flippers.f_test_hold_eos.main_coil),
             call(self.machine.flippers.f_test_hold_eos.eos_switch, self.machine.flippers.f_test_hold_eos.main_coil),
             call(self.machine.flippers.f_test_hold_eos.switch, self.machine.flippers.f_test_hold_eos.hold_coil)]
        )

    def test_flipper_with_settings(self):
        flipper = self.machine.flippers.f_test_flippers_with_settings
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        flipper.enable()
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
        self.assertEqual(
            (flipper.switch.get_configured_switch(),
             flipper.main_coil.get_configured_driver()),
            self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule._mock_call_args_list[0][0])

        self.assertEqual(10, flipper.main_coil.get_configured_driver().config['pulse_ms'])

        self.machine.default_platform.clear_hw_rule = MagicMock()
        flipper.disable()

        self.assertEqual(1, self.machine.default_platform.clear_hw_rule.called)
        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            flipper.switch.get_configured_switch(),
            flipper.main_coil.get_configured_driver())

        self.machine.settings.set_setting_value("flipper_power", 0.8)
        self.advance_time_and_run()

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()
        flipper.enable()
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
        self.assertEqual(
            (flipper.switch.get_configured_switch(),
             flipper.main_coil.get_configured_driver()),
            self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule._mock_call_args_list[0][0])

        self.assertEqual(8, flipper.main_coil.get_configured_driver().config['pulse_ms'])

    def test_sw_flip_and_release(self):

        self.machine.coils.c_flipper_main.enable = MagicMock()
        self.machine.coils.c_flipper_main.disable = MagicMock()
        self.machine.flippers.f_test_hold_eos.sw_flip()
        self.machine.coils.c_flipper_main.enable.assert_called_once_with()

        self.machine.flippers.f_test_hold_eos.sw_release()
        self.machine.coils.c_flipper_main.disable.assert_called_once_with()
