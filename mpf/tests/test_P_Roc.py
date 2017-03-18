from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock, call
from mpf.platforms import p_roc_common, p_roc


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
            else:
                raise AssertionError("cannot decode {}".format(device_str))

        else:
            raise AssertionError("asd")


class TestPRoc(MpfTestCase):
    def getConfigFile(self):
        if "wpc" in self._testMethodName:
            return "wpc.yaml"
        else:
            return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/p_roc/'

    def get_platform(self):
        return 'p_roc'

    def _normalize(self, type_name):
        if type_name == "pdb":
            return MockPinProcModule.MachineTypePDB
        elif type_name == "wpc":
            return MockPinProcModule.MachineTypeWPC
        else:
            raise AssertionError("Invalid type")

    def setUp(self):
        p_roc_common.pinproc_imported = True
        p_roc_common.pinproc = MockPinProcModule()
        p_roc.pinproc = p_roc_common.pinproc
        self.pinproc = MagicMock()
        p_roc_common.pinproc.PinPROC = MagicMock(return_value=self.pinproc)
        p_roc_common.pinproc.normalize_machine_type = self._normalize
        p_roc_common.pinproc.driver_state_pulse = MagicMock(
            return_value="driver_state_pulse")
        self.pinproc.switch_get_states = MagicMock(return_value=[0, 1] + [0] * 100)
        self.pinproc.read_data = MagicMock(return_value=0x12345678)
        super().setUp()

    def test_pulse_and_hold(self):
        self.assertEqual("P-Roc Board 1", self.machine.coils.c_test.hw_driver.get_board_name())
        # pulse coil A1-B1-2
        self.machine.coils.c_test.pulse()
        # A1-B1-2 -> address 16 + 8 + 2 = 26 in P3-Roc
        # for 23ms (from config)
        number = self.machine.coils.c_test.hw_driver.number
        self.machine.coils.c_test.hw_driver.proc.driver_pulse.assert_called_with(
            number, 23)
        assert not self.machine.coils.c_test.hw_driver.proc.driver_schedule.called

    def test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()

    def test_allow_enable(self):
        self.machine.coils.c_test_allow_enable.enable()
        number = self.machine.coils.c_test_allow_enable.hw_driver.number
        self.machine.coils.c_test.hw_driver.proc.driver_schedule.assert_called_with(
            number=number, cycle_seconds=0, now=True, schedule=0xffffffff)

    def test_hw_rule_pulse(self):
        self.machine.autofires.ac_slingshot_test.enable()
        self.machine.coils.c_slingshot_test.platform.proc.switch_update_rule.assert_any_call(
            40, 'closed_nondebounced',
            {'notifyHost': False, 'reloadActive': True},
            ["driver_state_pulse"], False)

    def test_initial_switches(self):
        self.assertEqual(0x1234, self.machine.default_platform.version)
        self.assertEqual(0x5678, self.machine.default_platform.revision)

        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_000"))
        self.assertTrue(self.machine.switch_controller.is_active("s_direct"))

    def test_switches(self):
        self.machine.default_platform.proc.switch_update_rule.assert_has_calls([
            call(23, 'closed_debounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(23, 'open_debounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(24, 'closed_nondebounced', {'notifyHost': True, 'reloadActive': False}, [], False),
            call(24, 'open_nondebounced', {'notifyHost': True, 'reloadActive': False}, [], False),
        ], any_order=True)

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

    def test_dmd_update(self):
        # test configure
        self.machine.default_platform.configure_dmd()

        self.pinproc.dmd_update_config.assert_called_with(high_cycles=[1, 2, 3, 4])

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(i % 256)

        dmd = self.machine.default_platform.dmd

        dmd.proc = MagicMock()

        dmd.update(frame)

        dmd.dmd.set_data.assert_called_with(frame)
        dmd.proc.dmd_draw.assert_called_with(dmd.dmd)

        # frame displayed
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 5, 'value': 123}])

        self.advance_time_and_run(0.04)
        dmd.proc.dmd_draw.assert_called_with(dmd.dmd)

        # draw broken frame
        dmd.dmd.set_data = MagicMock()

        # test set frame to buffer
        frame = bytearray()
        for i in range(1234):
            frame.append(i % 256)
        self.pinproc.update(frame)

        # should not be rendered
        assert not dmd.dmd.set_data.called

    def test_pdb_matrix_light(self):
        # very simple check for matrix config
        self.pinproc.driver_update_group_config.assert_has_calls(
            [call(4, 100, 5, 0, 0, True, True, True, True)]
        )

        # test enable of matrix light
        assert not self.machine.lights.test_pdb_light.hw_drivers["white"].proc.driver_patter.called
        self.machine.lights.test_pdb_light.on()
        self.advance_time_and_run(.02)
        self.machine.lights.test_pdb_light.hw_drivers["white"].proc.driver_patter.assert_called_with(
            32, 8, 0, 0, True
        )

        # test disable of matrix light
        assert not self.machine.lights.test_pdb_light.hw_drivers["white"].proc.driver_disable.called
        self.machine.lights.test_pdb_light.off()
        self.advance_time_and_run(.1)
        self.machine.lights.test_pdb_light.hw_drivers["white"].proc.driver_disable.assert_called_with(32)

    def test_pdb_gi_light(self):
        # test gi on
        device = self.machine.lights.test_gi
        num = self.machine.coils.test_gi.hw_driver.number
        device.hw_drivers["white"].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"].driver.hw_driver.proc.driver_schedule = MagicMock()
        device.color("white")
        self.advance_time_and_run(.1)
        device.hw_drivers["white"].driver.hw_driver.proc.driver_schedule.assert_has_calls([
            call(now=True, number=num, cycle_seconds=0, schedule=4294967295)])
        device.hw_drivers["white"].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"].driver.hw_driver.proc.driver_schedule = MagicMock()

        device.color([128, 128, 128])
        self.advance_time_and_run(.1)
        device.hw_drivers["white"].driver.hw_driver.proc.driver_patter.assert_has_calls([
            call(num, 1, 1, 0, True)])
        device.hw_drivers["white"].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"].driver.hw_driver.proc.driver_schedule = MagicMock()

        device.color([245, 245, 245])
        self.advance_time_and_run(.1)
        device.hw_drivers["white"].driver.hw_driver.proc.driver_patter.assert_has_calls([
            call(num, 7, 1, 0, True)])
        device.hw_drivers["white"].driver.hw_driver.proc.driver_patter = MagicMock()
        device.hw_drivers["white"].driver.hw_driver.proc.driver_schedule = MagicMock()

        # test gi off
        device.hw_drivers["white"].driver.hw_driver.proc.driver_disable = MagicMock()
        device.color("off")
        self.advance_time_and_run(.1)
        device.hw_drivers["white"].driver.hw_driver.proc.driver_disable.assert_has_calls([
            call(num)])

    def test_load_wpc(self):
        # make sure p-roc properly initialises with WPC config
        pass
