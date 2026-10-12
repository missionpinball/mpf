"""Test led groups."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestLightGroups(MpfTestCase):

    def get_config_file(self):
        return 'light_groups.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/light/'

    def test_color(self):
        self.machine.light_stripes['stripe1'].color(RGBColor("red"))
        self.advance_time_and_run(1)
        self.assertLightColor("stripe1_light_0", "red")
        self.assertLightColor("stripe1_light_1", "red")
        self.assertLightColor("stripe1_light_2", "red")
        self.assertLightColor("stripe1_light_3", "red")
        self.assertLightColor("stripe1_light_4", "red")

    def test_config_stripe_1(self):
        self.assertEqual("led-10-r", self.machine.lights["stripe1_light_0"].hw_drivers["red"][0].number)
        self.assertListEqual(["test", "stripe1"], self.machine.lights["stripe1_light_0"].config['tags'])
        self.assertEqual("led-11-r", self.machine.lights["stripe1_light_1"].hw_drivers["red"][0].number)
        self.assertEqual("led-12-r", self.machine.lights["stripe1_light_2"].hw_drivers["red"][0].number)
        self.assertEqual("led-13-r", self.machine.lights["stripe1_light_3"].hw_drivers["red"][0].number)
        self.assertEqual("led-14-r", self.machine.lights["stripe1_light_4"].hw_drivers["red"][0].number)
        self.assertListEqual(["test", "stripe1"], self.machine.lights["stripe1_light_4"].config['tags'])

    def test_config_stripe_2(self):
        self.assertEqual("led-7-200-r", self.machine.lights["stripe2_light_0"].hw_drivers["red"][0].number)
        self.assertEqual(10, self.machine.lights["stripe2_light_0"].config['x'])
        self.assertEqual(20, self.machine.lights["stripe2_light_0"].config['y'])
        self.assertEqual("led-7-201-r", self.machine.lights["stripe2_light_1"].hw_drivers["red"][0].number)
        self.assertEqual(15, self.machine.lights["stripe2_light_1"].config['x'])
        self.assertEqual(20, self.machine.lights["stripe2_light_1"].config['y'])

    def test_config_stripe_3(self):
        self.assertEqual("led-ABC-123", self.machine.lights["stripe3_light_0"].hw_drivers["red"][0].number)
        self.assertEqual("led-ABC-123+1", self.machine.lights["stripe3_light_0"].hw_drivers["green"][0].number)
        self.assertEqual("led-ABC-123+2", self.machine.lights["stripe3_light_0"].hw_drivers["blue"][0].number)
        self.assertEqual("led-ABC-123+3", self.machine.lights["stripe3_light_0"].hw_drivers["white"][0].number)
        self.assertEqual("led-ABC-123+4", self.machine.lights["stripe3_light_1"].hw_drivers["red"][0].number)

    def test_config_stripe_4(self):
        self.assertEqual("led-ex-8-r", self.machine.lights["l_example_light_098"].hw_drivers["red"][0].number)
        self.assertEqual("led-ex-8-g", self.machine.lights["l_example_light_098"].hw_drivers["green"][0].number)
        self.assertEqual("led-ex-8-b", self.machine.lights["l_example_light_098"].hw_drivers["blue"][0].number)
        self.assertEqual("led-ex-9-r", self.machine.lights["l_example_light_099"].hw_drivers["red"][0].number)
        self.assertEqual("led-ex-9-g", self.machine.lights["l_example_light_099"].hw_drivers["green"][0].number)
        self.assertEqual("led-ex-10-r", self.machine.lights["l_example_light_100"].hw_drivers["red"][0].number)
        self.assertEqual("led-ex-12-r", self.machine.lights["l_example_light_102"].hw_drivers["red"][0].number)

    def test_config_stripe_5(self):
        self.assertEqual("led-ex-2-0-r", self.machine.lights["l_example-2_light_9"].hw_drivers["red"][0].number)
        self.assertEqual("led-ex-2-0-g", self.machine.lights["l_example-2_light_9"].hw_drivers["green"][0].number)
        self.assertEqual("led-ex-2-0-b", self.machine.lights["l_example-2_light_9"].hw_drivers["blue"][0].number)
        self.assertEqual("led-ex-2-1-r", self.machine.lights["l_example-2_light_10"].hw_drivers["red"][0].number)
        self.assertEqual("led-ex-2-1-g", self.machine.lights["l_example-2_light_10"].hw_drivers["green"][0].number)
        self.assertEqual("led-ex-2-2-r", self.machine.lights["l_example-2_light_11"].hw_drivers["red"][0].number)

    def test_config_rings(self):
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

    def test_config_neoSeg_0(self):  # 8 digit
        self.assertEqual("led-0-0-0", self.machine.lights["neoSeg_0_light_0"].hw_drivers["white"][0].number)
        self.assertEqual("led-0-0-0+1", self.machine.lights["neoSeg_0_light_1"].hw_drivers["white"][0].number)
        self.assertEqual("led-0-0-0+2", self.machine.lights["neoSeg_0_light_2"].hw_drivers["white"][0].number)
        self.assertEqual("neoSeg_0_light_119", self.machine.lights["neoSeg_0_light_119"].name)

        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[0].name, self.machine.lights["neoSeg_0_light_95"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[1].name, self.machine.lights["neoSeg_0_light_90"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[2].name, self.machine.lights["neoSeg_0_light_93"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[3].name, self.machine.lights["neoSeg_0_light_82"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[4].name, self.machine.lights["neoSeg_0_light_85"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[5].name, self.machine.lights["neoSeg_0_light_89"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[20].name, self.machine.lights["neoSeg_0_light_103"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[40].name, self.machine.lights["neoSeg_0_light_66"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[60].name, self.machine.lights["neoSeg_0_light_5"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[80].name, self.machine.lights["neoSeg_0_light_13"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[100].name, self.machine.lights["neoSeg_0_light_36"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_0"].lights[119].name, self.machine.lights["neoSeg_0_light_35"].name)

    def test_config_neoSeg_1(self):  # 2 digit
        self.assertEqual("led-0-0-120", self.machine.lights["neoSeg_1_light_0"].hw_drivers["white"][0].number)
        self.assertEqual("led-0-0-120+1", self.machine.lights["neoSeg_1_light_1"].hw_drivers["white"][0].number)
        self.assertEqual("led-0-0-120+2", self.machine.lights["neoSeg_1_light_2"].hw_drivers["white"][0].number)
        self.assertEqual("neoSeg_1_light_29", self.machine.lights["neoSeg_1_light_29"].name)

        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[0].name, self.machine.lights["neoSeg_1_light_5"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[5].name, self.machine.lights["neoSeg_1_light_29"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[10].name, self.machine.lights["neoSeg_1_light_21"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[15].name, self.machine.lights["neoSeg_1_light_14"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[20].name, self.machine.lights["neoSeg_1_light_13"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[25].name, self.machine.lights["neoSeg_1_light_15"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_1"].lights[29].name, self.machine.lights["neoSeg_1_light_20"].name)

    def test_config_neoSeg_2(self):  # 8 digit on rgb-ordered channels
        self.assertEqual("led-0-1-0", self.machine.lights["neoSeg_2_light_0"].hw_drivers["white"][0].number)
        self.assertEqual("led-0-1-0+1", self.machine.lights["neoSeg_2_light_1"].hw_drivers["white"][0].number)
        self.assertEqual("neoSeg_2_light_119", self.machine.lights["neoSeg_2_light_119"].name)

        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[0].name, self.machine.lights["neoSeg_2_light_95"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[1].name, self.machine.lights["neoSeg_2_light_91"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[2].name, self.machine.lights["neoSeg_2_light_94"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[3].name, self.machine.lights["neoSeg_2_light_81"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[4].name, self.machine.lights["neoSeg_2_light_84"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[5].name, self.machine.lights["neoSeg_2_light_89"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[20].name, self.machine.lights["neoSeg_2_light_102"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[40].name, self.machine.lights["neoSeg_2_light_67"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[60].name, self.machine.lights["neoSeg_2_light_5"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[80].name, self.machine.lights["neoSeg_2_light_12"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[100].name, self.machine.lights["neoSeg_2_light_37"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_2"].lights[119].name, self.machine.lights["neoSeg_2_light_35"].name)

    def test_config_neoSeg_3(self):  # 2 digit on rgb-ordered channels
        self.assertEqual("led-0-1-120", self.machine.lights["neoSeg_3_light_0"].hw_drivers["white"][0].number)
        self.assertEqual("led-0-1-120+1", self.machine.lights["neoSeg_3_light_1"].hw_drivers["white"][0].number)
        self.assertEqual("neoSeg_3_light_29", self.machine.lights["neoSeg_3_light_29"].name)

        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[0].name, self.machine.lights["neoSeg_3_light_5"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[5].name, self.machine.lights["neoSeg_3_light_29"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[10].name, self.machine.lights["neoSeg_3_light_22"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[15].name, self.machine.lights["neoSeg_3_light_14"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[20].name, self.machine.lights["neoSeg_3_light_12"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[25].name, self.machine.lights["neoSeg_3_light_16"].name)
        self.assertEqual(self.machine.neoseg_displays["neoSeg_3"].lights[29].name, self.machine.lights["neoSeg_3_light_20"].name)
