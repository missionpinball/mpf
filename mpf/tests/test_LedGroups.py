"""Test led groups."""
from mpf.devices.led import Led

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase

from mpf.core.config_player import ConfigPlayer


class TestLedPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'led_groups.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/led/'

    def test_color(self):
        self.machine.light_stripes['stripe1'].color(RGBColor("red"))
        self.advance_time_and_run(1)
        self.assertLightColor("stripe1_light_10", "red")
        self.assertLightColor("stripe1_light_11", "red")
        self.assertLightColor("stripe1_light_12", "red")
        self.assertLightColor("stripe1_light_13", "red")
        self.assertLightColor("stripe1_light_14", "red")

    def test_config(self):
        # stripe 1
        self.assertEqual("10-r", self.machine.lights["stripe1_light_10"].hw_drivers["red"].number)
        self.assertListEqual(["test", "stripe1"], self.machine.lights["stripe1_light_10"].config['tags'])
        self.assertEqual("11-r", self.machine.lights["stripe1_light_11"].hw_drivers["red"].number)
        self.assertEqual("12-r", self.machine.lights["stripe1_light_12"].hw_drivers["red"].number)
        self.assertEqual("13-r", self.machine.lights["stripe1_light_13"].hw_drivers["red"].number)
        self.assertEqual("14-r", self.machine.lights["stripe1_light_14"].hw_drivers["red"].number)
        self.assertListEqual(["test", "stripe1"], self.machine.lights["stripe1_light_14"].config['tags'])

        # stripe 2
        self.assertEqual("7-200-r", self.machine.lights["stripe2_light_200"].hw_drivers["red"].number)
        self.assertEqual(10, self.machine.lights["stripe2_light_200"].config['x'])
        self.assertEqual(20, self.machine.lights["stripe2_light_200"].config['y'])
        self.assertEqual("7-201-r", self.machine.lights["stripe2_light_201"].hw_drivers["red"].number)
        self.assertEqual(15, self.machine.lights["stripe2_light_201"].config['x'])
        self.assertEqual(20, self.machine.lights["stripe2_light_201"].config['y'])

        # ring 1
        self.assertEqual("20-r", self.machine.lights["ring1_light_20"].hw_drivers["red"].number)
        self.assertEqual("21-r", self.machine.lights["ring1_light_21"].hw_drivers["red"].number)
        self.assertEqual("22-r", self.machine.lights["ring1_light_22"].hw_drivers["red"].number)
        self.assertEqual("23-r", self.machine.lights["ring1_light_23"].hw_drivers["red"].number)
        self.assertEqual("24-r", self.machine.lights["ring1_light_24"].hw_drivers["red"].number)
        # 90 degree
        self.assertEqual(103, self.machine.lights["ring1_light_20"].config['x'])
        self.assertEqual(50, self.machine.lights["ring1_light_20"].config['y'])
        # 180 degree
        self.assertEqual(100, self.machine.lights["ring1_light_23"].config['x'])
        self.assertEqual(47, self.machine.lights["ring1_light_23"].config['y'])
        # 270 degree
        self.assertEqual(97, self.machine.lights["ring1_light_26"].config['x'])
        self.assertEqual(50, self.machine.lights["ring1_light_26"].config['y'])
        # 360/0 degree
        self.assertEqual(100, self.machine.lights["ring1_light_29"].config['x'])
        self.assertEqual(53, self.machine.lights["ring1_light_29"].config['y'])