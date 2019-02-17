import time

import sys

from mpf.tests.MpfTestCase import MpfTestCase, test_config
from unittest.mock import MagicMock, call
from mpf.platforms import p_roc_common, p_roc


class MockDMD():
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.data = None

    def set_data(self, data):
        self.data = data


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

    def aux_command_jump(self, number):
        return "jump" + str(number)

    def aux_command_disable(self):
        return "disable"

    def aux_command_output_custom(self, arg1, arg2, arg3, arg4, arg5):
        return "output_custom_" + str(arg1) + "_" + str(arg2) + "_" + str(arg3) + "_" + str(arg4) + "_" + str(arg5)

    def aux_command_delay(self, delay):
        return "delay_" + str(delay)

    def decode(self, machine_type, device_str):
        if machine_type == MockPinProcModule.MachineTypePDB:
            # for PDB it will just return str as int
            return int(device_str)
        elif machine_type == MockPinProcModule.MachineTypeWPC:
            if device_str == "fllm":
                return 38
            elif device_str == "c01":
                return 40
            elif device_str == "sd1":
                return 8
            elif device_str == "sf1":
                return 0
            elif device_str == "s26":
                return 53
            elif device_str == "l11":
                return 80
            elif device_str == "g01":
                return 72
            elif device_str == "c02":
                return 9902
            elif device_str == "c23":
                return 9923
            elif device_str == "c24":
                return 9924
            elif device_str == "c25":
                return 9925
            else:
                raise AssertionError("cannot decode {}".format(device_str))

        else:
            raise AssertionError("Unknown Machine Type {}".format(machine_type))


class TestPRoc(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/p_roc/'

    def get_platform(self):
        # no force platform. we are testing p_roc and p_roc + snux
        return False

    def _normalize(self, type_name):
        if type_name == "pdb":
            return MockPinProcModule.MachineTypePDB
        elif type_name == "wpc":
            return MockPinProcModule.MachineTypeWPC
        else:
            raise AssertionError("Invalid type")

    def read_data(self, module, address):
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

    def setUp(self):
        if sys.version_info[0] == 3 and sys.version_info[1] == 4:
            # this fails on python 3.4 because of some asyncio bugs
            self.skipTest("Test is unstable in Python 3.4")
            return
        self._sync_count = 0
        self.expected_duration = 2
        p_roc_common.pinproc_imported = True
        p_roc_common.pinproc = MockPinProcModule()
        p_roc.pinproc = p_roc_common.pinproc
        self.pinproc = MagicMock(return_value=True)
        self.pinproc.aux_command_disable = MagicMock(return_value="disable")
        self.pinproc.aux_command_delay = MagicMock(return_value="delay")
        self.pinproc.aux_command_output_custom = MagicMock(return_value="output_custom")
        self.pinproc.aux_command_jump = MagicMock(return_value="jump")
        self.pinproc.read_data = self.read_data
        self.pinproc.aux_send_commands = MagicMock(return_value=True)
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
        self.pinproc.dmd_update_config = MagicMock(return_value=True)
        p_roc_common.pinproc.PinPROC = MagicMock(return_value=self.pinproc)
        p_roc_common.pinproc.normalize_machine_type = self._normalize
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

        self._memory = {
            0x00: {         # manager
                0x00: 0,            # chip id
                0x01: 0x00020006,   # version
                0x03: 0x0000,       # dip switches
            }
        }

        self.pinproc.aux_send_commands = MagicMock(return_value=True)
        super().setUp()

        self.pinproc.aux_send_commands.assert_called_with(0, ["disable"] + ["jump0"] * 254)

    def test_platform(self):
        self._test_initial_switches()
        self._test_switches()
        self._test_pulse_and_hold()
        self._test_pdb_matrix_light()
        self._test_alpha_display()
        self._test_allow_enable()
        self._test_hw_rule_pulse()
        self._test_dmd_update()
        self._test_pdb_gi_light()
        self._test_enable_exception()

        # test hardware scan
        info_str = """Firmware Version: 2 Firmware Revision: 6 Hardware Board ID: 0
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_pulse_and_hold(self):
        self.assertEqual("PD-16 Board 1 Bank 1", self.machine.coils.c_test.hw_driver.get_board_name())
        # pulse coil A1-B1-2
        self.machine.coils.c_test.pulse()
        self.wait_for_platform()
        # A1-B1-2 -> address 16 + 8 + 2 = 26 in P3-Roc
        # for 23ms (from config)
        number = self.machine.coils.c_test.hw_driver.number
        self.pinproc.driver_pulse.assert_called_with(
            number, 23)
        assert not self.pinproc.driver_schedule.called

    def _test_alpha_display(self):
        self.pinproc.aux_send_commands = MagicMock(return_value=True)
        self.machine.segment_displays.display1.add_text("1234", key="score")
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.aux_send_commands.assert_has_calls([
            call(0, ['disable', 'output_custom_0_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_1_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_2_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_3_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_4_0_8_False_0', 'output_custom_6_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_5_0_8_False_0', 'output_custom_91_0_9_False_0', 'output_custom_8_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_6_0_8_False_0', 'output_custom_79_0_9_False_0', 'output_custom_8_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_7_0_8_False_0', 'output_custom_102_0_9_False_0', 'output_custom_8_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_8_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_9_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_10_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_11_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_12_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_13_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_14_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_15_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40']),
            call(0, ["jump1"])
        ], any_order=False)

        self.pinproc.aux_send_commands = MagicMock(return_value=True)
        self.machine.segment_displays.display1.remove_text_by_key("score")
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.aux_send_commands.assert_has_calls([
            call(0, ['disable', 'output_custom_0_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_1_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_2_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_3_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_4_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_5_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_6_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_7_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_8_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_9_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_10_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_11_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_12_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_13_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_14_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40', 'output_custom_15_0_8_False_0', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_350', 'output_custom_0_0_11_False_0', 'output_custom_0_0_12_False_0', 'delay_2', 'output_custom_0_0_9_False_0', 'output_custom_0_0_10_False_0', 'delay_40']),
            call(0, ["jump1"])
        ], any_order=False)

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()

    def _test_allow_enable(self):
        self.machine.coils.c_test_allow_enable.enable()
        self.wait_for_platform()
        number = self.machine.coils.c_test_allow_enable.hw_driver.number
        self.pinproc.driver_schedule.assert_called_with(
            number, 0xffffffff, 0, True)

    def _test_hw_rule_pulse(self):
        self.machine.coils.c_slingshot_test.hw_driver.state = MagicMock(return_value=8)
        self.machine.autofires.ac_slingshot_test.enable()
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_any_call(
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
              'waitForFirstTimeSlot': False}], False)
        self.machine.autofires.ac_slingshot_test.disable()

    def _test_initial_switches(self):
        self.assertMachineVarEqual(2, "p_roc_version")
        self.assertMachineVarEqual(6, "p_roc_revision")

        self.assertEqual(0x2, self.machine.default_platform.version)
        self.assertEqual(0x6, self.machine.default_platform.revision)

        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_000"))
        self.assertTrue(self.machine.switch_controller.is_active("s_direct"))

    def _test_switches(self):
        self.wait_for_platform()
        self.pinproc.switch_update_rule.assert_has_calls([
            call(23, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(23, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(24, 'closed_nondebounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(24, 'open_nondebounced', {'notifyHost': True, 'reloadActive': False}, [], False),
        ], any_order=True)

        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        # closed debounced -> switch active
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 1, 'value': 23}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        # open debounces -> inactive
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 2, 'value': 23}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))

        self.assertFalse(self.machine.switch_controller.is_active("s_test_no_debounce"))
        # closed non debounced -> should be active
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 3, 'value': 24}])
        self.wait_for_platform()
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_no_debounce"))

        # open non debounced -> should be inactive
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 4, 'value': 24}])
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.advance_time_and_run(.1)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_no_debounce"))

    def _test_dmd_update(self):

        self.machine.default_platform.pinproc.DMDBuffer = MockDMD
        self.pinproc.dmd_draw = MagicMock(return_value=True)

        # test configure
        self.machine.default_platform.configure_dmd()
        self.wait_for_platform()

        self.pinproc.dmd_update_config.assert_called_with([1, 2, 3, 4])

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(i % 256)

        dmd = self.machine.default_platform.dmd

        dmd.update(frame)
        self.wait_for_platform()

        self.assertEqual(self.pinproc.dmd_draw.call_args[0][0].data, frame)

        # frame displayed
        self.pinproc.get_events = MagicMock(return_value=[
            {'type': 5, 'value': 123}])

        self.advance_time_and_run(0.04)
        self.wait_for_platform()
        self.assertEqual(self.pinproc.dmd_draw.call_args[0][0].data, frame)

        self.pinproc.dmd_draw = MagicMock(return_value=True)

        # test set frame to buffer
        frame = bytearray()
        for i in range(1234):
            frame.append(i % 256)

        dmd.update(frame)
        self.wait_for_platform()

        # should not be rendered
        assert not self.pinproc.dmd_draw.called

    def _test_pdb_matrix_light(self):
        # very simple check for matrix config
        self.pinproc.driver_update_group_config.assert_has_calls(
            [call(4, 100, 5, 0, 0, True, True, True, True)]
        )

        # test enable of matrix light
        assert not self.pinproc.driver_patter.called
        assert not self.pinproc.driver_schedule.called
        self.machine.lights.test_pdb_light.on()
        self.advance_time_and_run(.02)
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            32, 4294967295, 0, True
        )

        self.machine.lights.test_pdb_light.on(brightness=128)
        self.advance_time_and_run(.02)
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_called_with(
            32, 1, 1, 0, True
        )

        # test disable of matrix light
        assert not self.pinproc.driver_disable.called
        self.machine.lights.test_pdb_light.off()
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_called_with(32)

        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)
        self.pinproc.driver_disable = MagicMock(return_value=True)

        self.post_event("play_test_show")
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            32, 4294967295, 0, True
        )

        self.advance_time_and_run(1)
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_called_with(
            32, 3, 1, 0, True
        )

        self.advance_time_and_run(1)
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_called_with(32)
        self.pinproc.driver_disable = MagicMock(return_value=True)

        self.advance_time_and_run(1)
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            32, 4294967295, 0, True
        )
        self.advance_time_and_run(10)
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            32, 4294967295, 0, True
        )
        assert not self.pinproc.driver_disable.called

    def _test_pdb_gi_light(self):
        # test gi on
        device = self.machine.lights.test_gi
        num = self.machine.coils.test_gi.hw_driver.number
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)
        device.color("white")
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_has_calls([
            call(num, 4294967295, 0, True)])
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)

        device.color([128, 128, 128])
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_has_calls([
            call(num, 1, 1, 0, True)])
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)

        device.color([245, 245, 245])
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.driver_patter.assert_has_calls([
            call(num, 19, 1, 0, True)])
        self.pinproc.driver_patter = MagicMock(return_value=True)
        self.pinproc.driver_schedule = MagicMock(return_value=True)

        # test gi off
        self.pinproc.driver_disable = MagicMock(return_value=True)
        device.color("off")
        self.advance_time_and_run(.1)
        self.wait_for_platform()
        self.pinproc.driver_disable.assert_has_calls([
            call(num)])

    @test_config("wpc.yaml")
    def test_load_wpc(self):
        # make sure p-roc properly initialises with WPC config
        pass

    @test_config("snux.yaml")
    def test_load_snux(self):
        """Test snux."""
        # test enable
        self.machine.coils.c_flipper_enable_driver.enable()
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            9923, 0xffffffff, 0, True)

        # assert diag flash
        self.advance_time_and_run(1)
        self.wait_for_platform()
        self.pinproc.driver_pulse.assert_called_with(
            9924, 250)

        self.advance_time_and_run()
        self.wait_for_platform()

        # pulse a and c side
        self.pinproc.driver_schedule = MagicMock(return_value=True)
        self.machine.coils.c_test_a_side.pulse(100)
        self.advance_time_and_run(.001)
        self.machine.coils.c_test_c_side.pulse(50)
        self.advance_time_and_run(.040)
        self.wait_for_platform()
        self.advance_time_and_run(.001)
        self.wait_for_platform()
        self.pinproc.driver_pulse.assert_called_with(
            9902, 100)
        self.assertFalse(self.pinproc.driver_schedule.called)

        # afterwards service c side
        self.advance_time_and_run(.2)
        self.wait_for_platform()
        self.pinproc.driver_schedule.assert_called_with(
            9925, 0xffffffff, 0, True)
        self.pinproc.driver_pulse.assert_called_with(
            9902, 50)
