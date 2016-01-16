import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time
import math

class TestAccelerometer(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/accelerometer/'

    def _event_level1(self, **kwargs):
        self._level1 = True

    def _event_level2(self, **kwargs):
        self._level2 = True

    def test_leveling(self):
        accelerometer = self.machine.accelerometers.test_accelerometer

        self._level1 = False
        self._level2 = False
        self.machine.events.add_handler("event_level1", self._event_level1)
        self.machine.events.add_handler("event_level2", self._event_level2)

        # perfectly leveled
        accelerometer.update_acceleration(0.0, 0.0, 1.0)
        self.assertAlmostEqual(0.0, accelerometer.get_level_xz())
        self.assertAlmostEqual(0.0, accelerometer.get_level_yz())
        self.assertAlmostEqual(0.0, accelerometer.get_level_xyz())
        self.machine_run()
        self.assertFalse(self._level1)
        self.assertFalse(self._level2)

        # 90 degree on the side
        accelerometer.update_acceleration(1.0, 0.0, 0.0)
        self.assertAlmostEqual(math.pi/2, accelerometer.get_level_xz())
        self.assertAlmostEqual(0, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.pi/2, accelerometer.get_level_xyz())
        self.machine_run()
        self.assertTrue(self._level1)
        self.assertTrue(self._level2)

        # 90 degree on the back
        accelerometer.update_acceleration(0.0, 1.0, 0.0)
        self.machine_run()
        self.assertAlmostEqual(0, accelerometer.get_level_xz())
        self.assertAlmostEqual(math.pi/2, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.pi/2, accelerometer.get_level_xyz())

        # 45 degree on the side
        accelerometer.update_acceleration(0.5, 0.0, 0.5)
        self.machine_run()
        self.assertAlmostEqual(math.pi/4, accelerometer.get_level_xz())
        self.assertAlmostEqual(0, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.pi/4, accelerometer.get_level_xyz())

        # 3.01 degree
        self._level1 = False
        self._level2 = False
        accelerometer.update_acceleration(0.0, 0.05, 0.95)
        self.machine_run()
        self.assertTrue(self._level1)
        self.assertFalse(self._level2)

        # 6.34 degree
        self._level1 = False
        self._level2 = False
        accelerometer.update_acceleration(0.0, 0.1, 0.9)
        self.machine_run()
        self.assertTrue(self._level1)
        self.assertTrue(self._level2)

    def _event_hit1(self, **kwargs):
        self._hit1 = True

    def _event_hit2(self, **kwargs):
        self._hit2 = True

    def test_hits(self):
        accelerometer = self.machine.accelerometers.test_accelerometer

        # perfectly leveled
        accelerometer.update_acceleration(0.0, 0.0, 1.0)
        self.machine_run()

        self._hit1 = False
        self._hit2 = False
        self.machine.events.add_handler("event_hit1", self._event_hit1)
        self.machine.events.add_handler("event_hit2", self._event_hit2)

        # some noise
        accelerometer.update_acceleration(0.01, 0.05, 0.99)
        self.machine_run()
        self.assertFalse(self._hit1)
        self.assertFalse(self._hit2)

        # hit from the side
        accelerometer.update_acceleration(0.4, 0.4, 1.0)
        self.machine_run()
        self.assertTrue(self._hit1)
        self.assertFalse(self._hit2)
        self._hit1 = False
        self._hit2 = False

        # and it calms
        accelerometer.update_acceleration(0.01, 0.05, 0.99)
        self.machine_run()
        self.assertFalse(self._hit1)
        self.assertFalse(self._hit2)

        # strong hit from the side
        accelerometer.update_acceleration(1.5, 0.4, 1.0)
        self.machine_run()
        self.assertTrue(self._hit1)
        self.assertTrue(self._hit2)
