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
        self.machine.led_stripes['stripe1'].color(RGBColor("red"))
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor("red")), self.machine.leds["stripe1_led_10"].hw_driver.current_color)
        self.assertEqual(list(RGBColor("red")), self.machine.leds["stripe1_led_11"].hw_driver.current_color)
        self.assertEqual(list(RGBColor("red")), self.machine.leds["stripe1_led_12"].hw_driver.current_color)
        self.assertEqual(list(RGBColor("red")), self.machine.leds["stripe1_led_13"].hw_driver.current_color)
        self.assertEqual(list(RGBColor("red")), self.machine.leds["stripe1_led_14"].hw_driver.current_color)

    def test_config(self):
        # stripe 1
        self.assertEqual("10", self.machine.leds["stripe1_led_10"].hw_driver.number)
        self.assertListEqual(["test", "stripe1"], self.machine.leds["stripe1_led_10"].config['tags'])
        self.assertEqual("11", self.machine.leds["stripe1_led_11"].hw_driver.number)
        self.assertEqual("12", self.machine.leds["stripe1_led_12"].hw_driver.number)
        self.assertEqual("13", self.machine.leds["stripe1_led_13"].hw_driver.number)
        self.assertEqual("14", self.machine.leds["stripe1_led_14"].hw_driver.number)
        self.assertListEqual(["test", "stripe1"], self.machine.leds["stripe1_led_14"].config['tags'])

        # stripe 2
        self.assertEqual("7-200", self.machine.leds["stripe2_led_200"].hw_driver.number)
        self.assertEqual(10, self.machine.leds["stripe2_led_200"].config['x'])
        self.assertEqual(20, self.machine.leds["stripe2_led_200"].config['y'])
        self.assertEqual("7-201", self.machine.leds["stripe2_led_201"].hw_driver.number)
        self.assertEqual(15, self.machine.leds["stripe2_led_201"].config['x'])
        self.assertEqual(20, self.machine.leds["stripe2_led_201"].config['y'])
        self.assertEqual("7-202", self.machine.leds["stripe2_led_202"].hw_driver.number)
        self.assertEqual("7-203", self.machine.leds["stripe2_led_203"].hw_driver.number)
        self.assertEqual("7-204", self.machine.leds["stripe2_led_204"].hw_driver.number)

        # ring 1
        self.assertEqual("20", self.machine.leds["ring1_led_20"].hw_driver.number)
        self.assertEqual("21", self.machine.leds["ring1_led_21"].hw_driver.number)
        self.assertEqual("22", self.machine.leds["ring1_led_22"].hw_driver.number)
        self.assertEqual("23", self.machine.leds["ring1_led_23"].hw_driver.number)
        self.assertEqual("24", self.machine.leds["ring1_led_24"].hw_driver.number)
        # 90 degree
        self.assertEqual(103, self.machine.leds["ring1_led_20"].config['x'])
        self.assertEqual(50, self.machine.leds["ring1_led_20"].config['y'])
        # 180 degree
        self.assertEqual(100, self.machine.leds["ring1_led_23"].config['x'])
        self.assertEqual(47, self.machine.leds["ring1_led_23"].config['y'])
        # 270 degree
        self.assertEqual(97, self.machine.leds["ring1_led_26"].config['x'])
        self.assertEqual(50, self.machine.leds["ring1_led_26"].config['y'])
        # 360/0 degree
        self.assertEqual(100, self.machine.leds["ring1_led_29"].config['x'])
        self.assertEqual(53, self.machine.leds["ring1_led_29"].config['y'])