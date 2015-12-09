from MpfTestCase import MpfTestCase
from mpf.system.rgb_color import RGBColor


class TestRGBColor(MpfTestCase):

    def getConfigFile(self):
        return 'test_leds.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/show_controller/'

    def __init__(self, test_map):
        super(TestRGBColor, self).__init__(test_map)

    def test_default_color(self):
        # tests the default color
        color = RGBColor()
        self.assertEquals((0, 0, 0), color.rgb)
        self.assertEquals('Off', color.name)

    def test_static_utilities(self):
        # tests initializing a color by name
        self.assertEquals((240, 248, 255), RGBColor.string_to_rgb('AliceBlue'))
        self.assertEquals((240, 248, 255), RGBColor.name_to_rgb('AliceBlue'))
        self.assertEquals((240, 248, 255), RGBColor.hex_to_rgb('F0F8FF'))
        self.assertEquals((240, 248, 255), RGBColor.string_to_rgb('F0F8FF'))

    def test_properties(self):
        color1 = RGBColor()
        color1.name = 'DarkSlateBlue'
        self.assertEquals((72, 61, 139), color1.rgb)
        self.assertEquals(72, color1.red)
        self.assertEquals(61, color1.green)
        self.assertEquals(139, color1.blue)
        self.assertEquals('DarkSlateBlue', color1.name)
        self.assertEquals('483d8b', color1.hex)

        color2 = RGBColor()
        color2.rgb = (130, 130, 130)

        color_sum = color1 + color2
        self.assertEquals((202, 191, 255), color_sum.rgb)

        color_diff = color1 - color2
        self.assertEquals((0, 0, 9), color_diff.rgb)

        assert color1 != color2

        assert not (color1 == color2)

