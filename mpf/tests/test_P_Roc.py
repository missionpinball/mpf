from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock
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

    def decode(self, machine_type, device_str):
        assert machine_type == MockPinProcModule.MachineTypePDB
        # for PDB it will just return str as int
        return int(device_str)


class TestPRoc(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/p_roc/'

    def get_platform(self):
        return 'p_roc'

    def setUp(self):
        p_roc_common.pinproc_imported = True
        p_roc_common.pinproc = MockPinProcModule()
        pinproc = MagicMock()
        p_roc_common.pinproc.PinPROC = MagicMock(return_value=pinproc)
        p_roc_common.pinproc.normalize_machine_type = MagicMock(return_value=7)
        p_roc_common.pinproc.driver_state_pulse = MagicMock(
            return_value="driver_state_pulse")
        pinproc.switch_get_states = MagicMock(return_value=[0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        super().setUp()

    def test_pulse(self):
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
        self.machine.autofires.ac_slingshot_test.platform.proc.switch_update_rule.assert_called_with(
                40, 'closed_nondebounced',
                {'notifyHost': False, 'reloadActive': False},
                ["driver_state_pulse"], False)

    def test_initial_switches(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_000"))
        self.assertTrue(self.machine.switch_controller.is_active("s_test_001"))

    def test_switches(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 1, 'value': 23}])
        self.machine_run()
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 2, 'value': 23}])
        self.machine_run()
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
