"""Test accelerometer device."""
import math

from mpf.tests.MpfTestCase import MpfTestCase


class TestAccelerometer(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # this is the first test. give it some more time
        self.expected_duration = 2

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/accelerometer/'

    def _event_level1(self, **kwargs):
        del kwargs
        self._level1 = True

    def _event_level2(self, **kwargs):
        del kwargs
        self._level2 = True

    def test_leveling_different_base_angle(self):
        accelerometer = self.machine.accelerometers["test_accelerometer"]

        # change base angle to 6.5 degree
        accelerometer.config['level_x'] = math.sin(math.radians(6.5))
        accelerometer.config['level_y'] = 0
        accelerometer.config['level_z'] = math.cos(math.radians(6.5))

        # machine should be 6.5 degree off
        accelerometer.update_acceleration(0.0, 0.0, 1)
        self.assertAlmostEqual(math.radians(6.5), accelerometer.get_level_xz())
        self.assertAlmostEqual(0.0, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.radians(6.5), accelerometer.get_level_xyz())

        # add a small tilt
        accelerometer.update_acceleration(0.0, math.sin(math.radians(5)), math.cos(math.radians(5)))
        self.assertAlmostEqual(math.radians(6.5), accelerometer.get_level_xz())
        self.assertAlmostEqual(math.radians(5), accelerometer.get_level_yz())

        # leveled
        accelerometer.update_acceleration(math.sin(math.radians(6.5)), 0.0, math.cos(math.radians(6.5)))
        self.assertAlmostEqual(0.0, accelerometer.get_level_xz())
        self.assertAlmostEqual(0.0, accelerometer.get_level_yz())
        self.assertAlmostEqual(0.0, accelerometer.get_level_xyz())

        # leveled + tilt
        accelerometer.update_acceleration(math.sin(math.radians(6.5)) / math.cos(math.radians(6.5)),
                                          math.sin(math.radians(5)) / math.cos(math.radians(5)),
                                          1)
        self.assertAlmostEqual(0.0, accelerometer.get_level_xz())
        self.assertAlmostEqual(math.radians(5), accelerometer.get_level_yz())

    def test_leveling(self):
        accelerometer = self.machine.accelerometers["test_accelerometer"]

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
        for _ in range(100):
            accelerometer.update_acceleration(1.0, 0.0, 0.0)
        self.assertAlmostEqual(math.pi / 2, accelerometer.get_level_xz())
        self.assertAlmostEqual(0, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.pi / 2, accelerometer.get_level_xyz())
        self.machine_run()
        self.assertTrue(self._level1)
        self.assertTrue(self._level2)

        # 90 degree on the back
        accelerometer.update_acceleration(0.0, 1.0, 0.0)
        self.machine_run()
        self.assertAlmostEqual(0, accelerometer.get_level_xz())
        self.assertAlmostEqual(math.pi / 2, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.pi / 2, accelerometer.get_level_xyz())

        # 45 degree on the side
        accelerometer.update_acceleration(0.5, 0.0, 0.5)
        self.machine_run()
        self.assertAlmostEqual(math.pi / 4, accelerometer.get_level_xz())
        self.assertAlmostEqual(0, accelerometer.get_level_yz())
        self.assertAlmostEqual(math.pi / 4, accelerometer.get_level_xyz())

        # 3.01 degree
        self._level1 = False
        self._level2 = False
        for _ in range(100):
            accelerometer.update_acceleration(0.0, 0.05, 0.95)
        self.machine_run()
        self.assertTrue(self._level1)
        self.assertFalse(self._level2)

        # 6.34 degree
        self._level1 = False
        self._level2 = False
        for _ in range(100):
            accelerometer.update_acceleration(0.0, 0.1, 0.9)
        self.machine_run()
        self.assertTrue(self._level1)
        self.assertTrue(self._level2)

    def _event_hit1(self, **kwargs):
        del kwargs
        self._hit1 = True

    def _event_hit2(self, **kwargs):
        del kwargs
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
        accelerometer.update_acceleration(0.01, 0.05, 0.99)
        accelerometer.update_acceleration(0.01, 0.05, 0.99)
        accelerometer.update_acceleration(0.01, 0.05, 0.99)
        accelerometer.update_acceleration(0.01, 0.05, 0.99)
        self.machine_run()
        self.assertFalse(self._hit1)
        self.assertFalse(self._hit2)

        # strong hit from the side
        accelerometer.update_acceleration(1.5, 0.4, 1.0)
        self.machine_run()
        self.assertTrue(self._hit1)
        self.assertTrue(self._hit2)
