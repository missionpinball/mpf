from MpfTestCase import MpfTestCase
from mpf.system.rgb_color import RGBColor, RGBColorCorrectionProfile


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

        self.assertTrue(color1 != color2)
        self.assertFalse(color1 == color2)

    def test_color_correction(self):
        color = RGBColor(RGBColor.name_to_rgb('DarkGray'))
        self.assertEquals((169, 169, 169), color.rgb)

        # Tests default color correction profile (should be no correction)
        color_correction_profile = RGBColorCorrectionProfile()
        corrected_color = color_correction_profile.apply(color)
        self.assertEquals((169, 169, 169), corrected_color.rgb)

        # Test correction with default parameters
        color_correction_profile.generate_from_parameters(gamma=2.5,
                                                          whitepoint=(1.0, 1.0, 1.0),
                                                          linear_slope=1.0,
                                                          linear_cutoff=0.0)
        corrected_color = color_correction_profile.apply(color)
        self.assertEquals((91, 91, 91), corrected_color.rgb)

        # Test correction with new parameters
        color_correction_profile.generate_from_parameters(gamma=2.0,
                                                          whitepoint=(0.9, 0.85, 0.9),
                                                          linear_slope=0.75,
                                                          linear_cutoff=0.1)
        corrected_color = color_correction_profile.apply(color)
        self.assertEquals((77, 67, 77), corrected_color.rgb)



