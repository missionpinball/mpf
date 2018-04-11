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
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/p3_roc/'

    def get_platform(self):
        return False

    def read_data(self, module, address):
        if module not in self._memory or address not in self._memory[module]:
            return 0
        return self._memory[module][address]

    def setUp(self):
        self.expected_duration = 2
        p_roc_common.pinproc_imported = True
        p_roc_common.pinproc = MockPinProcModule()
        self.pinproc = MagicMock()
        p_roc_common.pinproc.PinPROC = MagicMock(return_value=self.pinproc)
        p_roc_common.pinproc.normalize_machine_type = MagicMock(return_value=7)
        p_roc_common.pinproc.decode = None  # should not be called and therefore fail
        p_roc_common.pinproc.driver_state_pulse = MagicMock(
            return_value={'driverNum': 8,
                          'outputDriveTime': 0,
                          'polarity': True,
                          'state': False,
                          'waitForFirstTimeSlot': False,
                          'timeslots': 0,
                          'patterOnTime': 0,
                          'patterOffTime': 0,
                          'patterEnable': False,
                          'futureEnable': False})

        p_roc_common.pinproc.driver_state_pulsed_patter = MagicMock(
            return_value={'driverNum': 9,
                          'outputDriveTime': 0,
                          'polarity': True,
                          'state': False,
                          'waitForFirstTimeSlot': False,
                          'timeslots': 0,
                          'patterOnTime': 0,
                          'patterOffTime': 0,
                          'patterEnable': False,
                          'futureEnable': False})

        p_roc_common.pinproc.driver_state_disable = MagicMock(
            return_value={'driverNum': 10,
                          'outputDriveTime': 0,
                          'polarity': True,
                          'state': False,
                          'waitForFirstTimeSlot': False,
                          'timeslots': 0,
                          'patterOnTime': 0,
                          'patterOffTime': 0,
                          'patterEnable': False,
                          'futureEnable': False})

        p_roc_common.pinproc.driver_state_patter = MagicMock(
            return_value={'driverNum': 11,
                          'outputDriveTime': 0,
                          'polarity': True,
                          'state': False,
                          'waitForFirstTimeSlot': False,
                          'timeslots': 0,
                          'patterOnTime': 0,
                          'patterOffTime': 0,
                          'patterEnable': False,
                          'futureEnable': False})

        self.pinproc.switch_get_states = MagicMock(return_value=[0, 1] + [0] * 100)
        self.pinproc.read_data = self.read_data
        self.pinproc.driver_update_group_config = MagicMock()

        self._memory = {
            0x00: {         # manager
                0x00: 0,            # chip id
                0x01: 0x00020006,   # version
                0x03: 0x0000,       # dip switches
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

    def test_platform(self):
        self._test_accelerometer()
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
        self._test_servo_via_i2c()
        self._test_initial_switches()
        self._test_switches()
        self._test_flipper_single_coil()
        self._test_flipper_two_coils()
        self._test_flipper_two_coils_with_eos()
        self._test_pdb_gi_light()
        self._test_hw_rule_hold_no_allow_enable()
        self._test_leds()
        self._test_leds_inverted()

        # test hardware scan
        info_str = """Firmware Version: 2 Firmware Revision: 6 Hardware Board ID: 0
SW-16 boards found:
 - Board: 0 Switches: 16 Device Type: A3 Board ID: 0
 - Board: 1 Switches: 16 Device Type: A3 Board ID: 13
 - Board: 2 Switches: 16 Device Type: A4 Board ID: 0
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_pulse(self):
        self.assertEqual("PD-16 Board 1 Bank 1", self.machine.coils.c_test.hw_driver.get_board_name())
        # pulse coil A1-B1-2
        self.machine.coils.c_test.pulse()
        number = self.machine.coils.c_test.hw_driver.number
        self.machine.coils.c_test.hw_driver.proc.driver_pulse.assert_called_with(
            number, 23)
        assert not self.machine.coils.c_test.hw_driver.proc.driver_schedule.called

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()

    def _test_allow_enable_disable(self):
        self.machine.coils.c_test_allow_enable.enable()
        number = self.machine.coils.c_test_allow_enable.hw_driver.number
        self.machine.coils.c_test_allow_enable.hw_driver.proc.driver_schedule.assert_called_with(
            number=number, cycle_seconds=0, now=True, schedule=0xffffffff)

        self.machine.coils.c_test_allow_enable.disable()
        self.machine.coils.c_test_allow_enable.hw_driver.proc.driver_disable.assert_called_with(number)

    def _test_hw_rule_pulse(self):
        self.machine.coils.c_slingshot_test.hw_driver.state = MagicMock(return_value=8)
        self.machine.autofires.ac_slingshot_test.enable()
        self.machine.coils.c_slingshot_test.platform.proc.switch_update_rule.assert_any_call(
            40, 'closed_nondebounced',
            {'notifyHost': False, 'reloadActive': True},
            [{'patterEnable': False,
              'patterOnTime': 0,
              'timeslots': 0,
              'futureEnable': False,
              'state': False,
              'patterOffTime': 0,
              'outputDriveTime': 0,
              'driverNum': 8,
              'polarity': True,
              'waitForFirstTimeSlot': False}],
            False)

        p_roc_common.pinproc.driver_state_pulse.assert_called_with(8, 10)

        # test disable
        self.machine.autofires.ac_slingshot_test.disable()

        self.machine.coils.c_slingshot_test.platform.proc.switch_update_rule.assert_has_calls([
            call(40, 'open_nondebounced', {'notifyHost': False, 'reloadActive': True}, []),
            call(40, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': True}, []),
            call(40, 'open_debounced', {'notifyHost': True, 'reloadActive': True}, []),
            call(40, 'closed_debounced', {'notifyHost': True, 'reloadActive': True}, []),
        ], any_order=True)

        self.machine.coils.c_slingshot_test.platform.proc.driver_disable.assert_called_with(8)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.machine.coils.c_coil_pwm_test.hw_driver.state = MagicMock(return_value=8)
        self.machine.coils.c_coil_pwm_test.platform.proc.switch_update_rule = MagicMock()
        self.machine.autofires.ac_switch_nc_test.enable()
        self.machine.coils.c_coil_pwm_test.platform.proc.switch_update_rule.assert_any_call(
            41, 'open_nondebounced',
            {'notifyHost': False, 'reloadActive': True},
            [{'patterEnable': False,
              'patterOnTime': 0,
              'timeslots': 0,
              'futureEnable': False,
              'state': False,
              'patterOffTime': 0,
              'outputDriveTime': 0,
              'driverNum': 8,
              'polarity': True,
              'waitForFirstTimeSlot': False}],
            False)

        p_roc_common.pinproc.driver_state_pulse.assert_called_with(8, 10)

        # test disable
        self.machine.autofires.ac_switch_nc_test.disable()
        self.machine.coils.c_coil_pwm_test.platform.proc.driver_disable.assert_called_with(8)

    def _test_hw_rule_pulse_disable_on_release(self):
        self.machine.coils.c_test.hw_driver.state = MagicMock(return_value=8)
        rule = self.machine.platform_controller.set_pulse_on_hit_and_release_rule(
            SwitchRuleSettings(switch=self.machine.switches.s_test, debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils.c_test, recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False}],
                False),
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

        p_roc_common.pinproc.driver_state_pulse.assert_called_with(8, 23)
        p_roc_common.pinproc.driver_state_disable.assert_called_with(8)

        self.machine.platform_controller.clear_hw_rule(rule)

    def _test_hw_rule_hold_pwm(self):
        return  # currently not cupported
        self.machine.coils.c_coil_pwm_test.hw_driver.state = MagicMock(return_value=8)
        self.machine.default_platform.set_hw_rule(
                sw_name="s_test",
                sw_activity=1,
                driver_name="c_coil_pwm_test",
                driver_action='hold',
                disable_on_release=False)

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
        self.machine.coils.c_test_allow_enable.hw_driver.state = MagicMock(return_value=8)
        rule = self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_rule(
            SwitchRuleSettings(switch=self.machine.switches.s_test, debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils.c_test_allow_enable, recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False}],
                False),
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

        p_roc_common.pinproc.driver_state_pulse.assert_called_with(8, 0)
        p_roc_common.pinproc.driver_state_disable.assert_called_with(8)
        self.machine.platform_controller.clear_hw_rule(rule)

    def _test_hw_rule_hold_no_allow_enable(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.platform_controller.set_pulse_on_hit_and_enable_and_release_rule(
                SwitchRuleSettings(switch=self.machine.switches.s_test, debounce=True, invert=False),
                DriverRuleSettings(driver=self.machine.coils.c_test, recycle=False),
                PulseRuleSettings(duration=23, power=1.0))

    def _test_hw_rule_multiple_pulse(self):
        self.machine.coils.c_test.hw_driver.state = MagicMock(return_value=8)
        self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.machine.switches.s_test, debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils.c_test, recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False}],
                False),
        ], any_order=True)

        p_roc_common.pinproc.driver_state_pulse.assert_called_with(8, 23)

        p_roc_common.pinproc.driver_state_pulse.assert_called_with = MagicMock()
        self.machine.default_platform.proc.switch_update_rule = MagicMock()

        # test setting the same rule again
        self.machine.coils.c_test.hw_driver.state = MagicMock(return_value=8)
        self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.machine.switches.s_test, debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils.c_test, recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False}],
                False),
        ], any_order=True)

        self.machine.coils.c_coil_pwm_test.hw_driver.state = MagicMock(return_value=9)
        self.machine.platform_controller.set_pulse_on_hit_rule(
            SwitchRuleSettings(switch=self.machine.switches.s_test, debounce=True, invert=False),
            DriverRuleSettings(driver=self.machine.coils.c_coil_pwm_test, recycle=False),
            PulseRuleSettings(duration=23, power=1.0))

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False),
        ], any_order=False)

        p_roc_common.pinproc.driver_state_pulse.assert_called_with(9, 23)

    def _test_servo_via_i2c(self):
        # assert on init
        self.machine.default_platform.proc.write_data.assert_has_calls([
            call(7, 0x8000, 0x11),
            call(7, 0x8001, 0x04),
            call(7, 0x80FE, 130),
            call(7, 0x8000, 0x01)
        ])
        self.machine.default_platform.proc.write_data = MagicMock()
        self.machine.servos.servo1.go_to_position(0)

        self.machine.default_platform.proc.write_data.assert_has_calls([
            call(7, 0x8012, 0),
            call(7, 0x8013, 0),
            call(7, 0x8014, 150),
            call(7, 0x8015, 0)
        ])
        self.machine.default_platform.proc.write_data = MagicMock()
        self.machine.servos.servo1.go_to_position(1)

        self.machine.default_platform.proc.write_data.assert_has_calls([
            call(7, 0x8012, 0),
            call(7, 0x8013, 0),
            call(7, 0x8014, 88),
            call(7, 0x8015, 2)
        ])

    def _test_initial_switches(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_000"))
        self.assertTrue(self.machine.switch_controller.is_active("s_flipper"))

    def _test_switches(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        # closed debounced -> switch active
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 1, 'value': 23}])
        self.advance_time_and_run(.01)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        # open debounces -> inactive
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 2, 'value': 23}])
        self.advance_time_and_run(.01)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))

        self.assertFalse(self.machine.switch_controller.is_active("s_test_no_debounce"))
        # closed non debounced -> should be active
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 3, 'value': 24}])
        self.advance_time_and_run(.01)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_no_debounce"))

        # open non debounced -> should be inactive
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 4, 'value': 24}])
        self.advance_time_and_run(.01)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_no_debounce"))

    def _test_accelerometer(self):
        # verify init
        self.machine.default_platform.proc.write_data.assert_has_calls([
            call(6, 0x0000, 0x000F),
            call(6, 0x012A, 0x0000),
            call(6, 0x010E, 0x0000),
            call(6, 0x012A, 0x0005),
            call(6, 0x012B, 0x0002),
            call(6, 0x0000, 0x1E0F)
        ])

        self.machine.accelerometers.p3_roc_accelerometer.update_acceleration = MagicMock()

        # process accelerometer event
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 8, 'value': 4096},
            {'type': 9, 'value': 0},
            {'type': 10, 'value': 8192}
        ])
        self.advance_time_and_run(.01)

        # check correct decoding of 2 complement
        self.machine.accelerometers.p3_roc_accelerometer.update_acceleration.assert_called_with(1.0, 0.0, -2.0)

    def _test_flipper_single_coil(self):
        # enable
        self.machine.default_platform.proc.switch_update_rule = MagicMock()
        self.machine.flippers.f_test_single.enable()

        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
            call(
                1, 'open_nondebounced',
                {'reloadActive': False, 'notifyHost': False},
                [{'state': False,
                  'waitForFirstTimeSlot': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'polarity': True,
                  'patterOffTime': 0,
                  'patterEnable': False,
                  'driverNum': 10,
                  'outputDriveTime': 0,
                  'futureEnable': False}],
                False),
            call(
                1, 'closed_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                [{'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 11,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False),
            call(1, 'open_debounced', {'reloadActive': False, 'notifyHost': True}, [], False),
            call(1, 'closed_debounced', {'reloadActive': False, 'notifyHost': True}, [], False)
        ], any_order=True)
        self.assertEqual(4, self.machine.default_platform.proc.switch_update_rule.call_count)

        # disable
        self.machine.default_platform.proc.switch_update_rule = MagicMock()
        self.machine.flippers.f_test_single.disable()
        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
            call(1, 'open_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'closed_nondebounced', {'notifyHost': False, 'reloadActive': False}, []),
            call(1, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, []),
            call(1, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, []),
        ], any_order=True)
        self.assertEqual(4, self.machine.default_platform.proc.switch_update_rule.call_count)

    def _test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.machine.default_platform.proc.switch_update_rule = MagicMock()
        self.machine.flippers.f_test_hold.enable()
        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
            call(
                1, 'open_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                [{'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 10,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 10,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False),
            call(
                1, 'closed_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                [
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 8,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 11,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False),
        ], any_order=True)

        self.machine.flippers.f_test_hold.disable()

    def _test_flipper_two_coils_with_eos(self):
        self.machine.default_platform.proc.switch_update_rule = MagicMock()
        self.machine.flippers.f_test_hold_eos.enable()
        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
            call(
                1, 'open_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                [{'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 10,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 10,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False),
            call(
                1, 'closed_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                [
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 11,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 11,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False),
            call(
                2, 'closed_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                [
                 {'patterEnable': False,
                  'patterOnTime': 0,
                  'timeslots': 0,
                  'futureEnable': False,
                  'state': False,
                  'patterOffTime': 0,
                  'outputDriveTime': 0,
                  'driverNum': 10,
                  'polarity': True,
                  'waitForFirstTimeSlot': False},
                 ],
                False)
        ], any_order=True)

        # disable
        self.machine.default_platform.proc.switch_update_rule = MagicMock()
        self.machine.flippers.f_test_hold_eos.disable()
        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
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
        assert not self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_patter.called
        assert not self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_schedule.called
        self.machine.lights.test_pdb_light.on()
        self.advance_time_and_run(.02)
        self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_schedule.assert_called_with(
            cycle_seconds=0, schedule=4294967295, now=True, number=32
        )

        self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_patter = MagicMock()
        self.machine.lights.test_pdb_light.on(brightness=128)
        self.advance_time_and_run(.02)
        self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_patter.assert_called_with(
            32, 1, 1, 0, True
        )

        # test disable of matrix light
        assert not self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_disable.called
        self.machine.lights.test_pdb_light.off()
        self.advance_time_and_run(.02)
        self.machine.lights.test_pdb_light.hw_drivers["white"][0].proc.driver_disable.assert_called_with(32)

    def _test_pdb_gi_light(self):
        # test gi on
        device = self.machine.lights.test_gi
        num = self.machine.coils.test_gi.hw_driver.number
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_schedule = MagicMock()
        device.color("white")
        self.advance_time_and_run(.1)
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_schedule.assert_has_calls([
            call(now=True, number=num, cycle_seconds=0, schedule=4294967295)])
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_schedule = MagicMock()

        device.color([128, 128, 128])
        self.advance_time_and_run(.1)
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_patter.assert_has_calls([
            call(num, 1, 1, 0, True)])
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_schedule = MagicMock()

        device.color([245, 245, 245])
        self.advance_time_and_run(.1)
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_patter.assert_has_calls([
            call(num, 19, 1, 0, True)])
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_schedule = MagicMock()

        # test gi off
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_disable = MagicMock()
        device.color("off")
        self.advance_time_and_run(.1)
        device.hw_drivers["white"][0].driver.hw_driver.proc.driver_disable.assert_has_calls([
            call(num)])

    def _test_leds(self):
        device = self.machine.lights.test_led
        device.hw_drivers['red'][0].proc.led_color = MagicMock()

        # test led on
        device.on()
        self.advance_time_and_run(1)
        device.hw_drivers['red'][0].proc.led_color.assert_has_calls([
            call(2, 1, 255),
            call(2, 2, 255),
            call(2, 3, 255)], True)
        device.hw_drivers['red'][0].proc.proc.led_color = MagicMock()

        # test led off
        device.off()
        self.advance_time_and_run(1)
        device.hw_drivers['red'][0].proc.led_color.assert_has_calls([
            call(2, 1, 0),
            call(2, 2, 0),
            call(2, 3, 0)], True)

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        device.hw_drivers['red'][0].proc.led_color.assert_has_calls([
            call(2, 1, 2),
            call(2, 2, 23),
            call(2, 3, 42)], True)

    def _test_leds_inverted(self):
        device = self.machine.lights.test_led_inverted
        device.hw_drivers['red'][0].proc.led_color = MagicMock()
        # test led on
        device.on()
        self.advance_time_and_run(1)
        device.hw_drivers['red'][0].proc.led_color.assert_has_calls([
            call(2, 4, 0),
            call(2, 5, 0),
            call(2, 6, 0)], True)
        device.hw_drivers['red'][0].proc.led_color = MagicMock()

        # test led off
        device.color("off")
        self.advance_time_and_run(1)
        device.hw_drivers['red'][0].proc.led_color.assert_has_calls([
            call(2, 4, 255),
            call(2, 5, 255),
            call(2, 6, 255)], True)

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        device.hw_drivers['red'][0].proc.led_color.assert_has_calls([
            call(2, 4, 255 - 2),
            call(2, 5, 255 -23),
            call(2, 6, 255 - 42)], True)
