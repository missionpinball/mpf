import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock, call
from mpf.platform import p3_roc


class TestP3Roc(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/p3_roc/'

    def getOptions(self):
        options = super().getOptions()
        options['force_platform'] = False
        return options

    def get_platform(self):
        return 'p3_roc'

    def setUp(self):
        p3_roc.pinproc_imported = True
        p3_roc.pinproc = MagicMock()
        p3_roc.pinproc.DriverCount = 256
        p3_roc.pinproc.decode = MagicMock(return_value="decode")
        p3_roc.pinproc.driver_state_pulse = MagicMock(
            return_value="driver_state_pulse")
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
        with self.assertRaises(AssertionError) as cm:
            self.machine.coils.c_test.enable()

    def test_allow_enable(self):
        self.machine.coils.c_test_allow_enable.enable()
        number = self.machine.coils.c_test_allow_enable.hw_driver.number
        self.machine.coils.c_test_allow_enable.hw_driver.proc.driver_schedule.assert_called_with(
                number=number, cycle_seconds=0, now=True, schedule=0xffffffff)

    def test_hw_rule_pulse(self):
        self.machine.autofires.ac_slingshot_test.enable()
        self.machine.autofires.ac_slingshot_test.platform.proc.switch_update_rule.assert_called_with(
                "decode", 'closed_nondebounced',
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
