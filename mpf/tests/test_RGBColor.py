import unittest

from mpf.core.rgba_color import RGBAColor

from mpf.core.rgb_color import RGBColor, RGBColorCorrectionProfile


class TestRGBColor(unittest.TestCase):

    def test_default_color(self):
        """Test the default color."""
        color = RGBColor()
        self.assertEqual((0, 0, 0), color.rgb)
        self.assertIn(color.name, ['black', 'off'])

    def test_rgba(self):
        # Test alpha channel."""
        color = RGBAColor("red")
        self.assertEqual((255, 0, 0), color.rgb)
        self.assertEqual((255, 0, 0, 255), color.rgba)
        self.assertEqual(255, color.opacity)
        self.assertEqual("red", color.name)

        color.rgba = (1, 2, 3, 4)
        self.assertEqual((1, 2, 3, 4), color.rgba)

        color = RGBAColor((255, 0, 0, 128))
        self.assertEqual((255, 0, 0), color.rgb)
        self.assertEqual((255, 0, 0, 128), color.rgba)
        self.assertEqual(128, color.opacity)
        self.assertEqual("red", color.name)

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

        color_brightness = RGBColor("red%50")
        self.assertEqual((127, 0, 0), color_brightness.rgb)
        color_brightness = RGBColor("AABBCC%50")
        self.assertEqual((85, 93, 102), color_brightness.rgb)
        color_red = RGBColor("red")
        self.assertEqual((127, 0, 0), (color_red * 0.5).rgb)

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
        color_correction_profile.generate_from_parameters()
        corrected_color = color_correction_profile.apply(color)
        self.assertEqual((91, 91, 91), corrected_color.rgb)

        # Test correction with new parameters
        color_correction_profile.generate_from_parameters(gamma=2.0,
                                                          whitepoint=(0.9, 0.85, 0.9),
                                                          linear_slope=0.75,
                                                          linear_cutoff=0.1)
        corrected_color = color_correction_profile.apply(color)
        self.assertEqual((77, 67, 77), corrected_color.rgb)

        # Test default correction profile
        default_profile = RGBColorCorrectionProfile.default()
        corrected_color = default_profile.apply(color)
        self.assertEqual((81, 81, 81), corrected_color.rgb)
        corrected_color = default_profile.apply(RGBColor((254, 254, 254)))
        self.assertEqual((252, 252, 252), corrected_color.rgb)

    def test_init_and_equal(self):
        black = RGBColor("black")
        color = RGBColor([1, 2, 3])
        self.assertEqual((1, 2, 3), color.rgb)
        color2 = RGBColor((1, 2, 3))
        color3 = RGBColor([1, 2, 3])
        color4 = RGBColor(color)
        color5 = RGBColor("010203")
        color6 = RGBColor("010203")
        color7 = RGBColor("")

        self.assertEqual(color2, color)
        self.assertEqual(color3, color)
        self.assertEqual(color4, color)
        self.assertEqual(color5, color)
        self.assertEqual(color6, color)
        self.assertEqual(color7, black)
        self.assertNotEqual(black, color)
        self.assertNotEqual(black, "010203")

        self.assertEqual("(1, 2, 3)", str(color5))

    def test_add_sub(self):
        color = RGBColor([1, 2, 3])
        color2 = color + (10, 10, 10)
        color3 = color + RGBColor((10, 10, 10))
        color4 = color2 - color3
        color5 = color2 - (11, 12, 13)
        self.assertEqual((11, 12, 13), color2.rgb)
        self.assertEqual((11, 12, 13), color3.rgb)
        self.assertEqual((0, 0, 0), color4.rgb)
        self.assertEqual((0, 0, 0), color5.rgb)
