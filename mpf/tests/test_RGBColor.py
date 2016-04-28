from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.rgb_color import RGBColor, RGBColorCorrectionProfile


class TestRGBColor(MpfTestCase):

    def test_default_color(self):
        # Tests the default color
        color = RGBColor()
        self.assertEqual((0, 0, 0), color.rgb)
        self.assertIn(color.name, ['black', 'off'])

    def test_off_color(self):
        # Tests the 'Off' color (nicely readable in LED show files)
        color = RGBColor()
        color.name = 'Off'
        self.assertEqual((0, 0, 0), color.rgb)
        self.assertIn(color.name, ['black', 'off'])

    def test_static_conversion_utilities(self):
        # Tests initializing a color by name or hex string value
        # (names and hex values are not case-sensitive)
        self.assertEqual((240, 248, 255), RGBColor.string_to_rgb('aliceblue'))
        self.assertEqual((240, 248, 255), RGBColor.name_to_rgb('aliceblue'))
        self.assertEqual((240, 248, 255), RGBColor.hex_to_rgb('F0F8FF'))
        self.assertEqual((240, 248, 255), RGBColor.string_to_rgb('F0F8FF'))
        with self.assertRaises(AssertionError):
            RGBColor.string_to_rgb('non_existant')
        self.assertEqual((0, 0, 0), RGBColor.name_to_rgb('non_existant'))
        self.assertEqual((240, 248, 255), RGBColor.hex_to_rgb('f0f8ff'))
        self.assertEqual((240, 248, 255), RGBColor.string_to_rgb('f0f8ff'))

    def test_construction(self):
        self.assertEqual((240, 248, 255), RGBColor('aliceblue').rgb)
        self.assertEqual((240, 248, 255), RGBColor('F0F8FF').rgb)
        self.assertEqual((240, 248, 255), RGBColor('f0f8ff').rgb)
        self.assertEqual((240, 248, 255), RGBColor((240, 248, 255)).rgb)

    def test_properties(self):
        color1 = RGBColor()
        color1.name = 'DarkSlateBlue'
        self.assertEqual((72, 61, 139), color1.rgb)
        self.assertEqual(72, color1.red)
        self.assertEqual(61, color1.green)
        self.assertEqual(139, color1.blue)
        self.assertEqual('darkslateblue', color1.name)
        self.assertEqual('483d8b', color1.hex)

        color2 = RGBColor()
        color2.rgb = (130, 130, 130)

        color_sum = color1 + color2
        self.assertEqual((202, 191, 255), color_sum.rgb)

        color_diff = color1 - color2
        self.assertEqual((0, 0, 9), color_diff.rgb)

        self.assertTrue(color1 != color2)
        self.assertFalse(color1 == color2)

    def test_color_blend(self):
        color1 = RGBColor((128, 64, 0))
        color2 = RGBColor((0, 32, 64))

        color_blend = RGBColor.blend(color1, color2, 0.25)
        self.assertEqual((96, 56, 16), color_blend.rgb)

        color_blend = RGBColor.blend(color1, color2, 0.5)
        self.assertEqual((64, 48, 32), color_blend.rgb)

        color_blend = RGBColor.blend(color1, color2, 0.75)
        self.assertEqual((32, 40, 48), color_blend.rgb)

    def test_color_correction(self):
        color = RGBColor(RGBColor.name_to_rgb('DarkGray'))
        self.assertEqual((169, 169, 169), color.rgb)

        # Tests default color correction profile (should be no correction)
        color_correction_profile = RGBColorCorrectionProfile()
        corrected_color = color_correction_profile.apply(color)
        self.assertEqual((169, 169, 169), corrected_color.rgb)

        # Test correction with default parameters
        color_correction_profile.generate_from_parameters(gamma=2.5,
                                                          whitepoint=(1.0, 1.0, 1.0),
                                                          linear_slope=1.0,
                                                          linear_cutoff=0.0)
        corrected_color = color_correction_profile.apply(color)
        self.assertEqual((91, 91, 91), corrected_color.rgb)

        # Test correction with new parameters
        color_correction_profile.generate_from_parameters(gamma=2.0,
                                                          whitepoint=(0.9, 0.85, 0.9),
                                                          linear_slope=0.75,
                                                          linear_cutoff=0.1)
        corrected_color = color_correction_profile.apply(color)
        self.assertEqual((77, 67, 77), corrected_color.rgb)
