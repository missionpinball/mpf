from unittest.mock import MagicMock

from mpf.platforms.interfaces.driver_platform_interface import PulseSettings

from mpf.core.platform import SwitchSettings, DriverSettings

from mpf.tests.MpfTestCase import MpfTestCase


class TestAutofire(MpfTestCase):
    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/autofire/'

    def test_hw_rule_pulse(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofire_coils["ac_test"].enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test"].hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=True)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofire_coils["ac_test"].disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test"].hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=True))

    def test_hw_rule_overwrites(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofire_coils["ac_test_overwrites"].enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test"].hw_switch, invert=False, debounce=True),
            DriverSettings(hw_driver=self.machine.coils["c_test"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=False)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofire_coils["ac_test_overwrites"].disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test"].hw_switch, invert=False, debounce=True),
            DriverSettings(hw_driver=self.machine.coils["c_test"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=False))

        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofire_coils["ac_test_overwrites2"].enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test_debounce_on"].hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test_recycle_off"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10), hold_settings=None, recycle=True)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofire_coils["ac_test_overwrites2"].disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test_debounce_on"].hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test_recycle_off"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10), hold_settings=None, recycle=True))

    def test_hw_rule_coil_and_switch_defaults(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofire_coils["ac_test_defaults"].enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test_debounce_on"].hw_switch, invert=False, debounce=True),
            DriverSettings(hw_driver=self.machine.coils["c_test_recycle_off"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10), hold_settings=None, recycle=False)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofire_coils["ac_test_defaults"].disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test_debounce_on"].hw_switch, invert=False, debounce=True),
            DriverSettings(hw_driver=self.machine.coils["c_test_recycle_off"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10), hold_settings=None, recycle=False))

    def test_hw_rule_pulse_inverted_switch(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofire_coils["ac_test_inverted"].enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test_nc"].hw_switch, invert=True, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test2"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=True)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofire_coils["ac_test_inverted"].disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test_nc"].hw_switch, invert=True, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test2"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=True))

    def test_hw_rule_pulse_inverted_autofire(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.machine.autofire_coils["ac_test_inverted2"].enable()

        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test"].hw_switch, invert=True, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test2"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=True)
        )

        self.machine.default_platform.clear_hw_rule = MagicMock()
        self.machine.autofire_coils["ac_test_inverted2"].disable()

        self.machine.default_platform.clear_hw_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_test"].hw_switch, invert=True, debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_test2"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=23), hold_settings=None, recycle=True))

    def test_disabled(self):
        """Verify that a disabled autofire coil doesn't post 'playfield_active'."""
        self.mock_event("playfield_active")
        self.machine_run()

        self.hit_and_release_switch("s_test_disabled")
        self.machine_run()
        self.assertEventNotCalled("playfield_active")

        self.machine.autofire_coils["ac_test_disabled"].enable()
        self.hit_and_release_switch("s_test_disabled")
        self.machine_run()
        self.assertEventCalled("playfield_active", times=1)

        self.machine.autofire_coils["ac_test_disabled"].disable()
        self.hit_and_release_switch("s_test_disabled")
        self.machine_run()
        self.assertEventCalled("playfield_active", times=1)

    def test_timeout(self):
        self.machine.autofire_coils["ac_test_timeout"].enable()
        self.machine_run()

        # 9 hits are ok
        for _ in range(9):
            self.hit_and_release_switch("s_test")
            self.machine_run()

        self.assertTrue(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        # 10th hit should disable it
        self.hit_and_release_switch("s_test")
        self.machine_run()
        self.assertFalse(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        # reenable after 500ms
        self.advance_time_and_run(.6)
        self.assertTrue(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        # exire the older hits
        self.advance_time_and_run(1)

        # 9 hits are ok
        for _ in range(9):
            self.hit_and_release_switch("s_test")
            self.machine_run()

        self.assertTrue(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        # wait 1s
        self.advance_time_and_run(1)

        # another 9 hits are ok
        for _ in range(9):
            self.hit_and_release_switch("s_test")
            self.machine_run()

        self.assertTrue(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        # 10th hit should disable it
        self.hit_and_release_switch("s_test")
        self.machine_run()
        self.assertFalse(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        self.advance_time_and_run(.2)

        # disable manually while disabled by too many hits
        self.machine.autofire_coils["ac_test_timeout"].disable()
        self.assertFalse(self.machine.autofire_coils["ac_test_timeout"]._enabled)

        # should not reenable
        self.advance_time_and_run(.4)
        self.assertFalse(self.machine.autofire_coils["ac_test_timeout"]._enabled)
