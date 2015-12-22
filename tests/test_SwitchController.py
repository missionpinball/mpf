import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestSwitchController(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/switch_controller/'


    def _callback(self):
         self.isActive = self.machine.switch_controller.is_active("s_test", ms=300)

    def testIsActiveTimeing(self):
        self.isActive = None

        self.machine.switch_controller.add_switch_handler(
                switch_name="s_test",
                callback=self._callback,
                state=1, ms=300)
        self.machine.switch_controller.process_switch("s_test", 1, True)

        self.advance_time_and_run(3)

        self.assertEqual(True, self.isActive)
