import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
from mpf.platform import p3_roc

class TestP3Roc(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/p3_roc/'

    def get_platform(self):
        return 'p3_roc'

    def setUp(self):
        p3_roc.pinproc_imported = True
        p3_roc.pinproc = MagicMock()
        p3_roc.pinproc.DriverCount = 256
        super(TestP3Roc, self).setUp()

    def test_pulse(self):
        # pulse coil A1-B1-2
        self.machine.coils.c_test.pulse()
        # A1-B1-2 -> address 16 + 8 + 2 = 26 in P3-Roc
        # for 23ms (from config)
        self.machine.coils.c_test.hw_driver.proc.driver_pulse.assert_called_with(26, 23)
        assert not self.machine.coils.c_test.hw_driver.proc.driver_schedule.called

    def test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError) as cm:
            self.machine.coils.c_test.enable()

    def test_allow_enable(self):
        self.machine.coils.c_test_allow_enable.enable()
        # A1-B1-3 -> address 16 + 8 + 3 = 27 in P3-Roc
        self.machine.coils.c_test.hw_driver.proc.driver_schedule.assert_called_with(
                number=27, cycle_seconds=0, now=True, schedule=0xffffffff)
