from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock, call
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

    def getOptions(self):
        options = super().getOptions()
        options['force_platform'] = False
        return options

    def get_platform(self):
        return 'p3_roc'

    def setUp(self):
        p_roc_common.pinproc_imported = True
        p_roc_common.pinproc = MockPinProcModule()
        pinproc = MagicMock()
        p_roc_common.pinproc.PinPROC = MagicMock(return_value=pinproc)
        p_roc_common.pinproc.normalize_machine_type = MagicMock(return_value=7)
        p_roc_common.pinproc.decode = None  # should not be called and therefore fail
        p_roc_common.pinproc.driver_state_pulse = MagicMock(
            return_value="driver_state_pulse")

        pinproc.switch_get_states = MagicMock(return_value=[0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        super().setUp()

    def test_pulse(self):
        # pulse coil A1-B1-2
        self.machine.coils.c_test.pulse()
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
        self.machine.coils.c_test_allow_enable.hw_driver.proc.driver_schedule.assert_called_with(
            number=number, cycle_seconds=0, now=True, schedule=0xffffffff)

    def test_hw_rule_pulse(self):
        self.machine.autofires.ac_slingshot_test.enable()
        self.machine.autofires.ac_slingshot_test.platform.proc.switch_update_rule.assert_called_with(
            40, 'closed_nondebounced',
            {'notifyHost': False, 'reloadActive': False},
            ["driver_state_pulse"], False)

    def test_servo_via_i2c(self):
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

    def test_initial_switches(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_000"))
        self.assertTrue(self.machine.switch_controller.is_active("s_test_001"))

    def test_switches(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        # closed non debounced -> nothing should happen
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 3, 'value': 23}])
        self.machine_run()
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))

        # closed debounced -> switch active
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 1, 'value': 23}])
        self.machine_run()
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        # open non debounces -> still active
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 4, 'value': 23}])
        self.machine_run()
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        # open debounces -> inactive
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 2, 'value': 23}])
        self.machine_run()
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))

        self.assertFalse(self.machine.switch_controller.is_active("s_test_no_debounce"))
        # closed non debounced -> should be active
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 3, 'value': 24}])
        self.machine_run()
        self.assertTrue(self.machine.switch_controller.is_active("s_test_no_debounce"))

        # open non debounced -> should be inactive
        self.machine.default_platform.proc.get_events = MagicMock(return_value=[
            {'type': 4, 'value': 24}])
        self.machine_run()
        self.assertFalse(self.machine.switch_controller.is_active("s_test_no_debounce"))
