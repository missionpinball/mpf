"""Test Light Position Mixin."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestLightPositions(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'light.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/light/'

    def test_light_positions(self):
        led1 = self.machine.lights.led1
        led2 = self.machine.lights.led2
        led3 = self.machine.lights.led3

        self.assertEqual(led1.x, 0.4)
        self.assertEqual(led1.y, 0.5)
        self.assertEqual(led1.z, 0)

        self.assertEqual(led2.x, 0.6)
        self.assertEqual(led2.y, 0.7)
        self.assertEqual(led2.z, None)
        
        self.assertEqual(led3.x, None)
        self.assertEqual(led3.y, None)
        self.assertEqual(led3.z, None)
        