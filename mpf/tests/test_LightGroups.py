"""Test led groups."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestLightGroups(MpfTestCase):

    def getConfigFile(self):
        return 'light_groups.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/light/'

    def test_color(self):
        self.machine.light_stripes['stripe1'].color(RGBColor("red"))
        self.advance_time_and_run(1)
        self.assertLightColor("stripe1_light_0", "red")
        self.assertLightColor("stripe1_light_1", "red")
        self.assertLightColor("stripe1_light_2", "red")
        self.assertLightColor("stripe1_light_3", "red")
        self.assertLightColor("stripe1_light_4", "red")

    def test_config(self):
        # stripe 1
        self.assertEqual("led-10-r", self.machine.lights["stripe1_light_0"].hw_drivers["red"][0].number)
        self.assertListEqual(["test", "stripe1"], self.machine.lights["stripe1_light_0"].config['tags'])
        self.assertEqual("led-11-r", self.machine.lights["stripe1_light_1"].hw_drivers["red"][0].number)
        self.assertEqual("led-12-r", self.machine.lights["stripe1_light_2"].hw_drivers["red"][0].number)
        self.assertEqual("led-13-r", self.machine.lights["stripe1_light_3"].hw_drivers["red"][0].number)
        self.assertEqual("led-14-r", self.machine.lights["stripe1_light_4"].hw_drivers["red"][0].number)
        self.assertListEqual(["test", "stripe1"], self.machine.lights["stripe1_light_4"].config['tags'])

        # stripe 2
        self.assertEqual("led-7-200-r", self.machine.lights["stripe2_light_0"].hw_drivers["red"][0].number)
        self.assertEqual(10, self.machine.lights["stripe2_light_0"].config['x'])
        self.assertEqual(20, self.machine.lights["stripe2_light_0"].config['y'])
        self.assertEqual("led-7-201-r", self.machine.lights["stripe2_light_1"].hw_drivers["red"][0].number)
        self.assertEqual(15, self.machine.lights["stripe2_light_1"].config['x'])
        self.assertEqual(20, self.machine.lights["stripe2_light_1"].config['y'])

        # ring 1
        self.assertEqual("led-20-r", self.machine.lights["ring1_light_0"].hw_drivers["red"][0].number)
        self.assertEqual("led-21-r", self.machine.lights["ring1_light_1"].hw_drivers["red"][0].number)
        self.assertEqual("led-22-r", self.machine.lights["ring1_light_2"].hw_drivers["red"][0].number)
        self.assertEqual("led-23-r", self.machine.lights["ring1_light_3"].hw_drivers["red"][0].number)
        self.assertEqual("led-24-r", self.machine.lights["ring1_light_4"].hw_drivers["red"][0].number)
        # 90 degree
        self.assertEqual(103, self.machine.lights["ring1_light_0"].config['x'])
        self.assertEqual(50, self.machine.lights["ring1_light_0"].config['y'])
        # 180 degree
        self.assertEqual(100, self.machine.lights["ring1_light_3"].config['x'])
        self.assertEqual(47, self.machine.lights["ring1_light_3"].config['y'])
        # 270 degree
        self.assertEqual(97, self.machine.lights["ring1_light_6"].config['x'])
        self.assertEqual(50, self.machine.lights["ring1_light_6"].config['y'])
        # 360/0 degree
        self.assertEqual(100, self.machine.lights["ring1_light_9"].config['x'])
        self.assertEqual(53, self.machine.lights["ring1_light_9"].config['y'])
