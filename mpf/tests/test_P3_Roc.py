from mpf.core.platform_controller import SwitchRuleSettings, DriverRuleSettings, PulseRuleSettings

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock, call
from mpf.platforms import p_roc_common


class MockPinProcModule(MagicMock):
    DriverCount = 256

    EventTypeAccelerometerIRQ = 11
    EventTypeAccelerometerX = 8
    EventTypeAccelerometerY = 9
    EventTypeAccelerometerZ = 10
    EventTypeBurstSwitchClosed = 7
    EventTypeBurstSwitchOpen = 6
    EventTypeDMDFrameDisplayed = 5
    EventTypeSwitchClosedDebounced = 1
    EventTypeSwitchClosedNondebounced = 3
    EventTypeSwitchOpenDebounced = 2
    EventTypeSwitchOpenNondebounced = 4

    MachineTypeCustom = 1
    MachineTypeInvalid = 0
    MachineTypePDB = 7
    MachineTypeSternSAM = 6
    MachineTypeSternWhitestar = 5
    MachineTypeWPC = 3
    MachineTypeWPC95 = 4
    MachineTypeWPCAlphanumeric = 2

    SwitchCount = 255
    SwitchNeverDebounceFirst = 192
    SwitchNeverDebounceLast = 255


class TestP3Roc(MpfTestCase):
    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/p3_roc/'

    def get_platform(self):
        return False

    def read_data(self, module, address):
        if module not in self._memory or address not in self._memory[module]:
            return 0
        return self._memory[module][address]

    def wait_for_platform(self):
        self._sync_count += 1
        num = self._sync_count
        result = self.machine.default_platform.run_proc_cmd_sync("_sync", num)
        assert result[0] == "sync"
        assert result[1] == num

    def _mock_loop(self):
        super()._mock_loop()
        self.loop._wait_for_external_executor = True

    def _driver_state_pulse(self, driver, milliseconds):
        driver["state"] = 1
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = False
        driver["outputDriveTime"] = milliseconds
        driver["patterOnTime"] = 0
        driver["patterOffTime"] = 0
        driver["patterEnable"] = False
        driver["futureEnable"] = False
        return driver

    def _driver_state_disable(self, driver):
        driver["state"] = 0
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = False
        driver["outputDriveTime"] = 0
        driver["patterOnTime"] = 0
        driver["patterOffTime"] = 0
        driver["patterEnable"] = False
        driver["futureEnable"] = False
        return driver

    def _driver_state_patter(self, driver, millisecondsOn, millisecondsOff, originalOnTime, now):
        driver["state"] = True
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = not now
        driver["outputDriveTime"] = originalOnTime
        driver["patterOnTime"] = millisecondsOn
        driver["patterOffTime"] = millisecondsOff
        driver["patterEnable"] = True
        driver["futureEnable"] = False
        return driver

    def _driver_pulsed_patter(self, driver, millisecondsOn, millisecondsOff, milliseconds_overall_patter_time, now):
        driver["state"] = True
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = not now
        driver["outputDriveTime"] = milliseconds_overall_patter_time
        driver["patterOnTime"] = millisecondsOn
        driver["patterOffTime"] = millisecondsOff
        driver["patterEnable"] = True
        driver["futureEnable"] = False
        return driver

    def setUp(self):
        self._sync_count = 0
        self.expected_duration = 2
        p_roc_common.PINPROC_IMPORTED = True
        p_roc_common.pinproc = MockPinProcModule()
        self.pinproc = MagicMock(return_value=True)
        p_roc_common.pinproc.PinPROC = MagicMock(return_value=self.pinproc)
        p_roc_common.pinproc.normalize_machine_type = MagicMock(return_value=7)
        p_roc_common.pinproc.decode = None  # should not be called and therefore fail
        p_roc_common.pinproc.driver_state_pulse = self._driver_state_pulse

        p_roc_common.pinproc.driver_state_pulsed_patter = self._driver_pulsed_patter

        p_roc_common.pinproc.driver_state_disable = self._driver_state_disable

        p_roc_common.pinproc.driver_state_patter = self._driver_state_patter

        self.pinproc.switch_get_states = MagicMock(return_value=[0, 1] + [0] * 100)
        self.pinproc.read_data = self.read_data
        self.pinproc.write_data = MagicMock(return_value=True)
        self.pinproc.flush = MagicMock(return_value=True)
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.pinproc.driver_update_group_config = MagicMock(return_value=True)
        self.pinproc.driver_update_global_config = MagicMock(return_value=True)
        self.pinproc.driver_update_state = MagicMock(return_value=True)
        self.pinproc.driver_pulse = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_disable = MagicMock(return_value=True)
        self.pinproc.reset = MagicMock(return_value=True)
        self.pinproc.get_events = MagicMock(return_value=[])

        self._memory = {
            0x00: {         # manager
                0x00: 0,            # chip id
                0x01: 0x0002000E,   # version
                0x03: 0x01FF,       # dip switches (will be overwritten by GPIO config)
                0x04: 0x80          # GPIO state (GPIO 7 active)
            },
            0x02: {         # switch controller
                0x1000: 0xA3,       # SW-16 Address 0 Reg 0
                0x1001: 0x00,       # SW-16 Address 0 Reg 1
                0x1040: 0xA3,       # SW-16 Address 1 Reg 0
                0x1041: 0x13,       # SW-16 Address 1 Reg 1
                0x1080: 0xA4,       # SW-16 Address 2 Reg 0
                0x1081: 0x00,       # SW-16 Address 2 Reg 1
            }
        }

        super().setUp()

        p_roc_common.pinproc.normalize_machine_type.assert_called_once_with("pdb")

    def test_platform(self):
        self._test_write_data_init()
        self._test_accelerometer()
        self._test_servo_via_i2c()
        self._test_digital_outputs()
        self._test_pulse()
        self._test_pdb_matrix_light()
        self._test_enable_exception()
        self._test_allow_enable_disable()
        self._test_hw_rule_pulse()
        self._test_hw_rule_pulse_inverted_switch()
        self._test_hw_rule_pulse_disable_on_release()
        self._test_hw_rule_hold_pwm()
        self._test_hw_rule_hold_allow_enable()
        self._test_hw_rule_multiple_pulse()
        self._test_pd_led_servo()
        self._test_initial_switches()
        self._test_switches()
        self._test_flipper_single_coil()
        self._test_flipper_two_coils()
        self._test_flipper_two_coils_with_eos()
        self._test_flipper_one_coil_with_eos()
        self._test_pdb_gi_light()
        self._test_hw_rule_hold_no_allow_enable()
        self._test_leds()
        self._test_leds_inverted()
        self._test_steppers()
        self._test_driver_bank_config()

        # test hardware scan
        info_str = """Firmware Version: 2 Firmware Revision: 14 Hardware Board ID: 1
SW-16 boards found:
 - Board: 0 Switches: 16 Device Type: A3 Board ID: 0
 - Board: 1 Switches: 16 Device Type: A3 Board ID: 13
 - Board: 2 Switches: 16 Device Type: A4 Board ID: 0
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())
        self.assertEqual(2, self.machine.variables["p_roc_version"])
        self.assertEqual(14, self.machine.variables["p_roc_revision"])
        self.assertEqual(1, self.machine.variables["p_roc_hardware_version"])

    def _test_write_data_init(self):
        """All tests which assert init stuff."""
        # verify init of accelerometer
        self.pinproc.write_data.assert_has_calls([
            call(6, 0x0000, 0x000F),
            call(6, 0x012A, 0x0000),
            call(6, 0x010E, 0x0000),
            call(6, 0x012A, 0x0005),
            call(6, 0x012B, 0x0002),
            call(6, 0x0000, 0x1E0F)
        ])

        # assert on init of servo controller on i2c
        self.pinproc.write_data.assert_has_calls([
            call(7, 0x8000, 0x11),
            call(7, 0x8001, 0x04),
            call(7, 0x80FE, 130),
            call(7, 0x8000, 0x01)
        ], any_order=True)

        # assert on init of gpios
        self.pinproc.write_data.assert_has_calls([
            call(0, 3, 0x2600),
        ], any_order=True)

        # reset write_data
        self.pinproc.write_data.reset_mock()

    def _test_pulse(self):
        self.assertEqual("PD-16 Board 1 Bank 1", self.machine.coils["c_test"].hw_driver.get_board_name())
        # pulse coil A1-B1-2
        self.machine.coils["c_test"].pulse()
        self.wait_for_platform()
        number = self.machine.coils["c_test"].hw_driver.number
        self.pinproc.driver_pulse.assert_called_with(number, 23)
        assert not self.pinproc.driver_schedule.called

        self.machine.coils["c_sling_pulse_power"].pulse()
        self.wait_for_platform()
        number = self.machine.coils["c_sling_pulse_power"].hw_driver.number
        self.pinproc.driver_pulsed_patter.assert_called_with(number, 1, 1, 12, True)

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils["c_test"].enable()

    def _test_allow_enable_disable(self):
        self.machine.coils["c_test_allow_enable"].enable()
        self.wait_for_platform()
        number = self.machine.coils["c_test_allow_enable"].hw_driver.number
        self.pinproc.driver_schedule.assert_called_with(
            number, 0xffffffff, 0, True)

        self.machine.coils["c_test_allow_enable"].disable()
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_called_with(number)

    def _test_hw_rule_pulse(self):
        coil_number = self.machine.coils["c_slingshot_test"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(40, 'open_nondebounced', {'notifyHost': False, 'reloadActive': True}, [], False),
            call(40, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': True},
                 [{'futureEnable': False, 'patterOffTime': 0, 'polarity': True, 'waitForFirstTimeSlot': False,
                   'timeslots': 0, 'patterOnTime': 0, 'outputDriveTime': 10, 'patterEnable': False, 'state': 1,
                   'driverNum': coil_number}], False),
            call(40, 'open_debounced', {'notifyHost': True, 'reloadActive': True}, [], False),
            call(40, 'closed_debounced', {'notifyHost': True, 'reloadActive': True}, [], False),
        ], any_order=True)

        self.pinproc.switch_update_rule = MagicMock(return_value=True)

        # test disable
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(40, 'open_nondebounced', {'notifyHost': False, 'reloadActive': True}, []),
            call(40, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': True}, []),
            call(40, 'open_debounced', {'notifyHost': True, 'reloadActive': True}, []),
            call(40, 'closed_debounced', {'notifyHost': True, 'reloadActive': True}, []),
        ], any_order=True)

        self.pinproc.driver_disable.assert_called_with(coil_number)

        # sling with pulse power
        coil_number = self.machine.coils["c_sling_pulse_power"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        self.machine.autofire_coils["ac_sling_pulse_power"].enable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(66, 'open_nondebounced', {'notifyHost': False, 'reloadActive': True}, [], False),
            call(66, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': True},
                 [{'driverNum': coil_number, 'outputDriveTime': 12, 'polarity': True, 'state': True,
                   'waitForFirstTimeSlot': False, 'timeslots': 0, 'patterOnTime': 1, 'patterOffTime': 1,
                   'patterEnable': True, 'futureEnable': False}], False),
            call(66, 'open_debounced', {'notifyHost': True, 'reloadActive': True}, [], False),
            call(66, 'closed_debounced', {'notifyHost': True, 'reloadActive': True}, [], False),
        ], any_order=True)

    def _test_hw_rule_pulse_inverted_switch(self):
        coil_number = self.machine.coils["c_coil_pwm_test"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.autofire_coils["ac_switch_nc_test"].enable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(41, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': True}, [], False),
            call(41, 'open_nondebounced', {'notifyHost': False, 'reloadActive': True},
                 [{'futureEnable': False, 'patterOffTime': 0, 'polarity': True, 'waitForFirstTimeSlot': False,
                   'timeslots': 0, 'patterOnTime': 0, 'outputDriveTime': 10, 'patterEnable': False, 'state': 1,
                   'driverNum': coil_number}], False),
            call(41, 'open_debounced', {'notifyHost': True, 'reloadActive': True}, [], False),
            call(41, 'closed_debounced', {'notifyHost': True, 'reloadActive': True}, [], False),
        ], any_order=True)

        # test disable
        self.machine.autofire_coils["ac_switch_nc_test"].disable()
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_called_with(coil_number)

    def _test_hw_rule_pulse_disable_on_release(self):
        coil_number = self.machine.coils["c_test"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        rule = self.machine.platform_controller.set_pulse_on_hit_and_release_rule(
            SwitchRuleSettings(switch=self.machine.switches["s_test"], debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils["c_test"], recycle=False),
            PulseRuleSettings(duration=23, power=1.0))
        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 0, 'patterEnable': False, 'outputDriveTime': 0, 'futureEnable': False}],
                 False),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 1, 'patterEnable': False, 'outputDriveTime': 23, 'futureEnable': False}],
                 False),
        ], any_order=True)

        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.platform_controller.clear_hw_rule(rule)
        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, []),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, []),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, []),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, []),
        ], any_order=True)

    def _test_hw_rule_hold_pwm(self):
        return  # currently not cupported
        self.machine.default_platform.set_hw_rule(
                sw_name="s_test",
                sw_activity=1,
                driver_name="c_coil_pwm_test",
                driver_action='hold',
                disable_on_release=False)

        self.pinproc.switch_update_rule.assert_has_calls([
            call(
                23, 'closed_debounced',
                {'notifyHost': True, 'reloadActive': False},
                [{'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 11,
                  'polarity': True,
                  'waitForFirstTimeSlot': False}],
                False),
        ])

        p_roc_common.pinproc.driver_state_patter.assert_called_with(8, 2, 8, 0, True)

        # now add disable rule
        self.machine.default_platform.set_hw_rule(
                sw_name="s_test",
                sw_activity=0,
                driver_name="c_coil_pwm_test",
                driver_action='disable',
                disable_on_release=False)

        self.pinproc.switch_update_rule.assert_has_calls([
            call(
                23, 'open_debounced',
                {'notifyHost': True, 'reloadActive': False},
                [{'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 10,
                  'polarity': True,
                  'waitForFirstTimeSlot': False}],
                False),
        ], any_order=True)

        p_roc_common.pinproc.driver_state_disable.assert_called_with(8)

        self.machine.default_platform.clear_hw_rule("s_test", "c_coil_pwm_test")

    def _test_hw_rule_hold_allow_enable(self):
        coil_number = self.machine.coils["c_test_allow_enable"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        rule = self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_rule(
            SwitchRuleSettings(switch=self.machine.switches["s_test"], debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils["c_test_allow_enable"], recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 0, 'patterEnable': False, 'outputDriveTime': 0, 'futureEnable': False}],
                 False),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 1, 'patterEnable': False, 'outputDriveTime': 0, 'futureEnable': False}],
                 False),
        ], any_order=True)

        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.platform_controller.clear_hw_rule(rule)
        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, []),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, []),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, []),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, []),
        ], any_order=True)


    def _test_hw_rule_hold_no_allow_enable(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_rule(
                SwitchRuleSettings(switch=self.machine.switches["s_test"], debounce=True, invert=False),
                DriverRuleSettings(driver=self.machine.coils["c_test"], recycle=False),
                PulseRuleSettings(duration=23, power=1.0))

    def _test_hw_rule_multiple_pulse(self):
        coil_number = self.machine.coils["c_test"].hw_driver.number
        coil_number2 = self.machine.coils["c_coil_pwm_test"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.machine.switches["s_test"], debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils["c_test"], recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 1, 'patterEnable': False, 'outputDriveTime': 23, 'futureEnable': False}],
                 False),
        ], any_order=True)

        self.pinproc.switch_update_rule = MagicMock(return_value=True)

        # test setting the same rule again
        self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.machine.switches["s_test"], debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils["c_test"], recycle=False),
            PulseRuleSettings(duration=23, power=1.0))
        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 1, 'patterEnable': False, 'outputDriveTime': 23, 'futureEnable': False}],
                 False),
        ], any_order=True)

        self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.machine.switches["s_test"], debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils["c_coil_pwm_test"], recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(23, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(23, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [
                {'patterOnTime': 0, 'driverNum': coil_number, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 1, 'patterEnable': False, 'outputDriveTime': 23, 'futureEnable': False},
                {'patterOnTime': 0, 'driverNum': coil_number2, 'waitForFirstTimeSlot': False, 'patterOffTime': 0,
                 'polarity': True,
                 'timeslots': 0, 'state': 1, 'patterEnable': False, 'outputDriveTime': 23, 'futureEnable': False},
            ],
                 False),
        ], any_order=True)

    def _test_servo_via_i2c(self):
        self.pinproc.write_data = MagicMock(return_value=True)
        self.machine.servos["servo1"].go_to_position(0)
        self.wait_for_platform()

        self.pinproc.write_data.assert_has_calls([
            call(7, 0x8012, 0),
            call(7, 0x8013, 0),
            call(7, 0x8014, 150),
            call(7, 0x8015, 0)
        ])
        self.pinproc.write_data = MagicMock(return_value=True)
        self.machine.servos["servo1"].go_to_position(1)
        self.wait_for_platform()

        self.pinproc.write_data.assert_has_calls([
            call(7, 0x8012, 0),
            call(7, 0x8013, 0),
            call(7, 0x8014, 88),
            call(7, 0x8015, 2)
        ])

    def _test_pd_led_servo(self):
        self.pinproc.write_data = MagicMock(return_value=True)
        self.machine.servos["servo_pd_led_0"].go_to_position(0)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 72),              # low byte of address (72)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 127),  # set servo position
            ], False)

        self.pinproc.write_data = MagicMock(return_value=True)
        self.machine.servos["servo_pd_led_0"].go_to_position(1)
        self.wait_for_platform()

        self.pinproc.write_data.assert_has_calls([
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 72),              # low byte of address (72)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set servo position
            ], False)

    def _test_initial_switches(self):
        self.assertSwitchState("s_test", 0)
        self.assertSwitchState("s_test_000", 0)
        self.assertSwitchState("s_flipper", 1)
        self.assertSwitchState("s_gpio0", 0)
        self.assertSwitchState("s_gpio7", 1)

    def _test_switches(self):
        self.assertSwitchState("s_test", 0)
        # closed debounced -> switch active
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 1, 'value': 23}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.assertSwitchState("s_test", 1)

        # open debounces -> inactive
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 2, 'value': 23}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.assertSwitchState("s_test", 0)

        self.assertSwitchState("s_test_no_debounce", 0)
        # closed non debounced -> should be active
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 3, 'value': 24}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.assertSwitchState("s_test_no_debounce", 1)

        # open non debounced -> should be inactive
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 4, 'value': 24}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.assertSwitchState("s_test_no_debounce", 0)

        self.pinproc.get_events = MagicMock(return_value=[])

        # test gpio changes
        self._memory[0][4] = 0x01   # gpio 7 low, gpio 0 high
        self.advance_time_and_run(.01)
        self.wait_for_platform()
        self.advance_time_and_run(.01)
        self.assertSwitchState("s_gpio0", 1)
        self.assertSwitchState("s_gpio7", 0)

    def _test_accelerometer(self):
        self.machine.accelerometers["p3_roc_accelerometer"].update_acceleration = MagicMock(return_value=True)

        # process accelerometer event
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 8, 'value': 4096},
            {'type': 9, 'value': 0},
            {'type': 10, 'value': 8192}
        ])
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.advance_time_and_run(.1)

        # check correct decoding of 2 complement
        self.machine.accelerometers["p3_roc_accelerometer"].update_acceleration.assert_called_with(1.0, 0.0, -2.0)

        self.pinproc.get_events = MagicMock(return_value=[])

    def _test_flipper_single_coil(self):
        coil_number = self.machine.coils["c_flipper_main"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.wait_for_platform()
        # enable
        self.machine.flippers["f_test_single"].enable()

        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(1, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, [
                {'timeslots': 0, 'waitForFirstTimeSlot': False, 'polarity': True, 'driverNum': coil_number,
                 'outputDriveTime': 11,
                 'futureEnable': False, 'patterEnable': True, 'patterOnTime': 3, 'patterOffTime': 5, 'state': True}],
                 False),
            call(1, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(1, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(1, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, [
                {'timeslots': 0, 'waitForFirstTimeSlot': False, 'polarity': True, 'driverNum': coil_number,
                 'outputDriveTime': 0,
                 'futureEnable': False, 'patterEnable': False, 'patterOnTime': 0, 'patterOffTime': 0, 'state': 0}],
                 False),
        ], any_order=True)

        # disable
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_single"].disable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(1, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(1, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
        ], any_order=True)
        self.assertEqual(4, self.pinproc.switch_update_rule.call_count)

    def _test_flipper_two_coils(self):
        coil_number = self.machine.coils["c_flipper_main"].hw_driver.number
        coil_number2 = self.machine.coils["c_flipper_hold"].hw_driver.number
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_hold"].enable()
        self.wait_for_platform()

        self.pinproc.switch_update_rule.assert_has_calls([
            call(1, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterEnable': False, 'waitForFirstTimeSlot': False, 'state': 0, 'timeslots': 0, 'patterOffTime': 0,
                 'outputDriveTime': 0, 'driverNum': coil_number, 'polarity': True, 'patterOnTime': 0,
                 'futureEnable': False},
                {'patterEnable': False, 'waitForFirstTimeSlot': False, 'state': 0, 'timeslots': 0, 'patterOffTime': 0,
                 'outputDriveTime': 0, 'driverNum': coil_number2, 'polarity': True, 'patterOnTime': 0,
                 'futureEnable': False}],
                 False),
            call(1, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(1, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterEnable': False, 'waitForFirstTimeSlot': False, 'state': 1, 'timeslots': 0, 'patterOffTime': 0,
                 'outputDriveTime': 10, 'driverNum': coil_number, 'polarity': True, 'patterOnTime': 0,
                 'futureEnable': False},
                {'patterEnable': True, 'waitForFirstTimeSlot': False, 'state': True, 'timeslots': 0, 'patterOffTime': 7,
                 'outputDriveTime': 10, 'driverNum': coil_number2, 'polarity': True, 'patterOnTime': 1,
                 'futureEnable': False}],
                 False),
            call(1, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
        ], any_order=True)

        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_hold"].disable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(1, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(1, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
        ], any_order=True)

    def _test_flipper_two_coils_with_eos(self):
        coil_number = self.machine.coils["c_flipper_main"].hw_driver.number
        coil_number2 = self.machine.coils["c_flipper_hold"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_hold_eos"].enable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(2, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(2, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(2, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(2, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterOnTime': 0, 'outputDriveTime': 0, 'timeslots': 0, 'patterOffTime': 0, 'polarity': True,
                 'driverNum': coil_number, 'state': 0, 'futureEnable': False, 'patterEnable': False,
                 'waitForFirstTimeSlot': False}], False),
            call(1, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterOnTime': 0, 'outputDriveTime': 0, 'timeslots': 0, 'patterOffTime': 0, 'polarity': True,
                 'driverNum': coil_number, 'state': 0, 'futureEnable': False, 'patterEnable': False,
                 'waitForFirstTimeSlot': False},
                {'patterOnTime': 0, 'outputDriveTime': 0, 'timeslots': 0, 'patterOffTime': 0, 'polarity': True,
                 'driverNum': coil_number2, 'state': 0, 'futureEnable': False, 'patterEnable': False,
                 'waitForFirstTimeSlot': False}], False),
            call(1, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(1, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(1, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterOnTime': 0, 'outputDriveTime': 10, 'timeslots': 0, 'patterOffTime': 0, 'polarity': True,
                 'driverNum': coil_number, 'state': True, 'futureEnable': False, 'patterEnable': False,
                 'waitForFirstTimeSlot': False},
                {'patterOnTime': 1, 'outputDriveTime': 10, 'timeslots': 0, 'patterOffTime': 7, 'polarity': True,
                 'driverNum': coil_number2, 'state': True, 'futureEnable': False, 'patterEnable': True,
                 'waitForFirstTimeSlot': False}], False)
        ], any_order=True)

        # disable
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_hold_eos"].disable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(1, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(1, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(2, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(2, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(2, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(2, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
        ], any_order=True)

    def _test_flipper_one_coil_with_eos(self):
        # single coil with eos
        coil_number = self.machine.coils["c_flipper_main"].hw_driver.number
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_single_eos"].enable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(2, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [], False),
            call(2, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(2, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(2, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, [
                {'driverNum': coil_number, 'outputDriveTime': 0, 'polarity': True, 'state': True,
                 'waitForFirstTimeSlot': False, 'timeslots': 0, 'patterOnTime': 3, 'patterOffTime': 5,
                 'patterEnable': True, 'futureEnable': False}], False),
            call(1, 'open_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterOnTime': 0, 'outputDriveTime': 0, 'timeslots': 0, 'patterOffTime': 0, 'polarity': True,
                 'driverNum': coil_number, 'state': 0, 'futureEnable': False, 'patterEnable': False,
                 'waitForFirstTimeSlot': False}], False),
            call(1, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(1, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(1, 'closed_nondebounced', {'reloadActive': False, 'notifyHost': False}, [
                {'patterOnTime': 3, 'outputDriveTime': 10, 'timeslots': 0, 'patterOffTime': 5, 'polarity': True,
                 'driverNum': coil_number, 'state': True, 'futureEnable': False, 'patterEnable': True,
                 'waitForFirstTimeSlot': False}], False),
        ], any_order=True)

        # disable
        self.pinproc.switch_update_rule = MagicMock(return_value=True)
        self.machine.flippers["f_test_single_eos"].disable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(1, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(1, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(2, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(2, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(2, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(2, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
        ], any_order=True)

    def _test_pdb_matrix_light(self):
        # very simple check for matrix config
        self.pinproc.driver_update_group_config.assert_has_calls(
            [call(4, 100, 5, 0, 0, True, True, True, True)]
        )

        # test enable of matrix light
        assert not self.pinproc.driver_patter.called
        assert not self.pinproc.driver_schedule.called
        self.machine.lights["test_pdb_light"].on()
        self.advance_time_and_run(.02)
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            32, 4294967295, 0, True
        )

        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.machine.lights["test_pdb_light"].on(brightness=128)
        self.advance_time_and_run(.02)
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_called_with(
            32, 1, 1, 0, True
        )

        # test disable of matrix light
        assert not self.pinproc.driver_disable.called
        self.machine.lights["test_pdb_light"].off()
        self.advance_time_and_run(.02)
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_called_with(32)

    def _test_pdb_gi_light(self):
        # test gi on
        device = self.machine.lights["test_gi"]
        num = self.machine.coils["test_gi"].hw_driver.number
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)
        device.color("white")
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_has_calls([
            call(num, 4294967295, 0, True)])
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)

        device.color([128, 128, 128])
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_has_calls([
            call(num, 1, 1, 0, True)])
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)

        device.color([245, 245, 245])
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_has_calls([
            call(num, 19, 1, 0, True)])
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)

        # test gi off
        self.pinproc.driver_disable = MagicMock(return_value=True)
        device.color("off")
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_has_calls([
            call(num)])

    def _test_leds(self):
        device = self.machine.lights["test_led"]
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led on
        device.on()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 1),               # low byte of address (1)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led off
        device.off()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 1),               # low byte of address (1)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 0),    # set color (0)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 0),    # set color (0)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 0),    # set color (0)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(.1)
        self.wait_for_platform()

        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 1),               # low byte of address (1)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 2),    # set color (2)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 23),   # set color (23)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 42),   # set color (42)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

        device = self.machine.lights["test_led2"]
        device.on()
        self.advance_time_and_run(1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 7),               # low byte of address (1)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led color with fade
        device.color(RGBColor((13, 37, 238)), fade_ms=42)
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # fade ms
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (3 << 8) | 10),   # set fade lower (42/4 = 10)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (4 << 8) | 0),    # set fade higher (0)
            # first LED addr
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 7),               # low byte of address (7)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 13),   # set color (13)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 37),   # set color (37)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 238),  # set color (238)
            ], False)

        self.advance_time_and_run(.5)
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led color with fade
        device.color(RGBColor((255, 37, 238)), fade_ms=20)
        self.machine.lights["test_led3"].color(RGBColor((253, 0, 0)), fade_ms=20)
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # fade ms
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (3 << 8) | 5),    # set fade lower (20/4 = 5)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (4 << 8) | 0),    # set fade higher (0)
            # first LED addr
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 7),               # low byte of address (7)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 255),   # set color (13)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 37),   # set color (37)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 238),  # set color (238)
            # forth LED (test_led3)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 253),  # set color (253)
            # fifth LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 0),  # set color (0)
            # sixth LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (2 << 8) | 0),  # set color (0)
            ], False)

    def _test_leds_inverted(self):
        device = self.machine.lights["test_led_inverted"]
        self.pinproc.write_data = MagicMock(return_value=True)
        # test led on
        device.on()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 4),               # low byte of address (4)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 0),    # set color (0)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 0),    # set color (0)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 0),    # set color (0)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led off
        device.color("off")
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 4),               # low byte of address (4)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 255),  # set color (255)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            # first LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | 4),               # low byte of address (4)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (6 << 8)),        # high byte of address (0)
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 253),  # set color (255 - 2)
            # second LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 232),  # set color (255 - 23)
            # third LED
            call(3, 3072, 0x01000000 | (2 & 0x3F) << 16 | (1 << 8) | 213),  # set color (255 - 42)
            ], False)
        self.pinproc.write_data = MagicMock(return_value=True)

    def _test_steppers(self):
        stepper1 = self.machine.steppers["stepper1"]
        stepper2 = self.machine.steppers["stepper2"]

        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 1, 'value': 64}, {'type': 1, 'value': 65}])
        self.wait_for_platform()
        self.advance_time_and_run(.01)
        self.wait_for_platform()
        self.assertSwitchState("s_stepper1_home", 1)
        self.assertSwitchState("s_stepper2_home", 1)
        self.pinproc.get_events = MagicMock(return_value=[])

        # test stepper 1
        self.pinproc.write_data = MagicMock()
        stepper1._move_to_absolute_position(11)
        self.advance_time_and_run(.1)
        self.wait_for_platform()

        self.pinproc.write_data.assert_has_calls([
            call(3, 3072, 0x1040000 + 11),
            call(3, 3072, 0x1040600),
            call(3, 3072, 0x1040700 + 23)
        ], True)

        # test stepper 2
        self.pinproc.write_data = MagicMock()
        stepper2._move_to_absolute_position(500)
        self.advance_time_and_run(.1)
        self.wait_for_platform()

        self.pinproc.write_data.assert_has_calls([
            call(3, 3072, 0x1040000 + (500 & 0xFF)),
            call(3, 3072, 0x1040600 + ((500 >> 8) & 0xFF)),
            call(3, 3072, 0x1040700 + 24)
        ], True)

        # move again. it should wait
        self.pinproc.write_data = MagicMock()
        stepper2._move_to_absolute_position(450)
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.assertEqual(0, self.pinproc.write_data.call_count)

        self.advance_time_and_run(1)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            call(3, 3072, 0x1040000 + 50),
            call(3, 3072, 0x1040600 + (1 << 7)),
            call(3, 3072, 0x1040700 + 24)
        ], True)

    def _test_digital_outputs(self):
        self.pinproc.write_data.reset_mock()

        self.machine.digital_outputs["d_gpio1"].enable()
        self.machine.digital_outputs["d_gpio5"].enable()
        self.advance_time_and_run(.01)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            call(0, 3, 0x2602),
            call(0, 3, 0x2622),
        ], any_order=False)

        self.pinproc.write_data.reset_mock()

        self.machine.digital_outputs["d_gpio1"].disable()
        self.advance_time_and_run(.01)
        self.wait_for_platform()
        self.pinproc.write_data.assert_has_calls([
            call(0, 3, 0x2620),
        ], any_order=False)

    def _test_driver_bank_config(self):
        """Check configured banks."""
        configured_banks = set()
        enabled_banks = []
        for call in self.pinproc.driver_update_group_config.mock_calls[4:]:
            configured_banks.add(call[1][2])
            if call[1][7]:
                enabled_banks.append(call[1][2])

        self.assertEqual({0, 1, 2, 3, 4, 5, 10, 11, 12, 13}, configured_banks)
        self.assertEqual([0, 1, 2, 3, 4, 5, 10, 11, 12, 13], sorted(enabled_banks))
