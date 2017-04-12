from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

from mpf.core.platform import SwitchSettings, DriverSettings

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

        self.machine.default_platform.set_pulse_on_hit_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_left_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_left_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=30),
                           hold_settings=None, recycle=False)
        )

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_left_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_left_hold.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=1.0), recycle=False)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.left_flipper.disable()
        self.assertFalse(self.machine.flippers.left_flipper._enabled)

        self.machine.default_platform.clear_hw_rule.assert_has_calls(
            [call(
                SwitchSettings(hw_switch=self.machine.switches.s_left_flipper.hw_switch, invert=False, debounce=False),
                DriverSettings(hw_driver=self.machine.coils.c_flipper_left_main.hw_driver,
                               pulse_settings=PulseSettings(power=1.0, duration=30),
                               hold_settings=None, recycle=False)
            ),
             call(
                 SwitchSettings(hw_switch=self.machine.switches.s_left_flipper.hw_switch, invert=False, debounce=False),
                 DriverSettings(hw_driver=self.machine.coils.c_flipper_left_hold.hw_driver,
                                pulse_settings=PulseSettings(power=1.0, duration=10),
                                hold_settings=HoldSettings(power=1.0), recycle=False)
            )
        ], any_order=True)

        self.machine.default_platform.set_pulse_on_hit_and_release_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        self.machine.flippers.left_flipper.enable()
        self.machine.default_platform.set_pulse_on_hit_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_left_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_left_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=30),
                           hold_settings=None, recycle=False)
        )

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_left_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_left_hold.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=1.0), recycle=False)
        )
