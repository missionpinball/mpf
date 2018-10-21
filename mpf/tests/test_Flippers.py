from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

from mpf.core.platform import SwitchSettings, DriverSettings

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
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=0.125), recycle=False)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_single.disable()

        self.assertEqual(1, self.machine.default_platform.clear_hw_rule.called)
        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=0.125), recycle=False)
        )

    def test_hold_with_eos(self):
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        self.machine.flippers.f_test_hold_eos.enable()

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_hold.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=1.0), recycle=False)
        )
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule.assert_called_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            SwitchSettings(hw_switch=self.machine.switches.s_flipper_eos.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=0.125), recycle=False)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.flippers.f_test_hold_eos.disable()

        self.machine.default_platform.clear_hw_rule.assert_has_calls([
            call(
                SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
                DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                               pulse_settings=PulseSettings(power=1.0, duration=10),
                               hold_settings=HoldSettings(power=0.125), recycle=False)
            ),
            call(
                SwitchSettings(hw_switch=self.machine.switches.s_flipper_eos.hw_switch, invert=False, debounce=False),
                DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                               pulse_settings=PulseSettings(power=1.0, duration=10),
                               hold_settings=HoldSettings(power=0.125), recycle=False)
            ),
            call(
                SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
                DriverSettings(hw_driver=self.machine.coils.c_flipper_hold.hw_driver,
                               pulse_settings=PulseSettings(power=1.0, duration=10),
                               hold_settings=HoldSettings(power=1.0), recycle=False)
            ),
        ], any_order = True)

    def test_flipper_with_settings(self):
        flipper = self.machine.flippers.f_test_flippers_with_settings
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()

        flipper.enable()
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=0.125), recycle=False)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        flipper.disable()

        self.assertEqual(1, self.machine.default_platform.clear_hw_rule.called)
        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=0.125), recycle=False))

        self.machine.settings.set_setting_value("flipper_power", 0.8)
        self.advance_time_and_run()

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()
        flipper.enable()
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_flipper.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.c_flipper_main.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=8),
                           hold_settings=HoldSettings(power=0.125), recycle=False)
        )

        self.assertEqual(8, flipper._get_pulse_ms())

    def test_sw_flip_and_release(self):
        self.machine.coils.c_flipper_main.enable = MagicMock()
        self.machine.coils.c_flipper_main.disable = MagicMock()
        self.post_event("flip_single")
        assert not self.machine.coils.c_flipper_main.enable.called

        self.machine.flippers.f_test_single.enable()
        self.post_event("flip_single")

        self.machine.coils.c_flipper_main.enable.assert_called_once_with()
        self.machine.coils.c_flipper_main.enable = MagicMock()

        self.post_event("release_single")
        self.machine.coils.c_flipper_main.disable.assert_called_once_with()

        # flip again
        self.post_event("flip_single")
        self.machine.coils.c_flipper_main.enable.assert_called_once_with()

        self.machine.coils.c_flipper_main.pulse = MagicMock()
        self.machine.coils.c_flipper_main.disable = MagicMock()
        self.machine.coils.c_flipper_hold.enable = MagicMock()
        self.machine.coils.c_flipper_hold.disable = MagicMock()
        self.machine.flippers.f_test_single.disable()

        # switch is not active. it should release the flipper
        self.machine.coils.c_flipper_main.disable.assert_called_once_with()
        self.machine.coils.c_flipper_main.disable = MagicMock()

        self.machine.flippers.f_test_hold_eos.enable()
        self.post_event("flip_hold")
        self.machine.coils.c_flipper_main.pulse.assert_called_once_with()
        self.machine.coils.c_flipper_hold.enable.assert_called_once_with()

        self.post_event("release_hold")
        self.machine.coils.c_flipper_main.disable.assert_called_once_with()
        self.machine.coils.c_flipper_hold.disable.assert_called_once_with()
