from mpf.tests.MpfGameTestCase import MpfGameTestCase
from mpf.core.rgb_color import RGBColor

class TestBlinkenlight(MpfGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_platform(self):
        return 'smart_virtual'

    def get_machine_path(self):
        return 'tests/machine_files/blinkenlight/'

    def test_add_color_to_one_blinkenlight(self):
        self.post_event('start_mode1')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.post_event('add_color_to_first_blinkenlight')
        self.assertPlaceholderEvaluates(1, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight2.num_colors')

    def test_add_color_to_two_blinkenlights(self):
        self.post_event('start_mode1')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.post_event('add_color_to_all_blinkenlights')
        self.assertPlaceholderEvaluates(1, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(1, 'device.blinkenlights.my_blinkenlight2.num_colors')

    def test_remove_color_from_one_blinkenlight(self):
        self.post_event('start_mode1')
        self.post_event('add_color_to_second_blinkenlight')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(1, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.post_event('remove_color_from_first_blinkenlight')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(1, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.post_event('remove_color_from_second_blinkenlight')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight2.num_colors')

    def test_remove_all_colors_from_all_blinkenlights(self):
        self.post_event('start_mode1')
        self.post_event('add_color_to_first_blinkenlight')
        self.post_event('add_color_to_second_blinkenlight')
        self.post_event('add_color_to_third_blinkenlight')
        self.post_event('add_color_to_all_blinkenlights')
        self.assertPlaceholderEvaluates(2, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(2, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.assertPlaceholderEvaluates(2, 'device.blinkenlights.my_blinkenlight3.num_colors')
        self.post_event('remove_all_colors_from_all_blinkenlights')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.assertPlaceholderEvaluates(0, 'device.blinkenlights.my_blinkenlight3.num_colors')

    def test_flashing_cycle(self):
        self.post_event('start_mode1')
        self.post_event('add_color_to_all_blinkenlights')
        self.post_event('add_color_to_first_blinkenlight')
        self.post_event('add_color_to_second_blinkenlight')
        self.post_event('add_color_to_third_blinkenlight')

        self.assertPlaceholderEvaluates(2, 'device.blinkenlights.my_blinkenlight1.num_colors')
        self.assertPlaceholderEvaluates(2, 'device.blinkenlights.my_blinkenlight2.num_colors')
        self.assertPlaceholderEvaluates(2, 'device.blinkenlights.my_blinkenlight3.num_colors')

        blinkenlight1 = self.machine.blinkenlights['my_blinkenlight1']
        blinkenlight2 = self.machine.blinkenlights['my_blinkenlight2']
        blinkenlight3 = self.machine.blinkenlights['my_blinkenlight3']

        blue = RGBColor('blue')
        green = RGBColor('green')
        red = RGBColor('red')
        yellow = RGBColor('yellow')
        purple = RGBColor('purple')
        cyan = RGBColor('cyan')
        off = RGBColor('off')

        self.assertEqual(blue,   blinkenlight1.light._color)
        self.assertEqual(green,  blinkenlight2.light._color)
        self.assertEqual(cyan,   blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(red,    blinkenlight1.light._color)
        self.assertEqual(green,  blinkenlight2.light._color)
        self.assertEqual(purple, blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(off,    blinkenlight1.light._color)
        self.assertEqual(yellow, blinkenlight2.light._color)
        self.assertEqual(cyan,   blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(blue,   blinkenlight1.light._color)
        self.assertEqual(yellow, blinkenlight2.light._color)
        self.assertEqual(purple, blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(red,    blinkenlight1.light._color)
        self.assertEqual(green,  blinkenlight2.light._color)
        self.assertEqual(cyan,   blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(off,    blinkenlight1.light._color)
        self.assertEqual(green,  blinkenlight2.light._color)
        self.assertEqual(purple, blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(blue,   blinkenlight1.light._color)
        self.assertEqual(yellow, blinkenlight2.light._color)
        self.assertEqual(cyan,   blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(red,    blinkenlight1.light._color)
        self.assertEqual(yellow, blinkenlight2.light._color)
        self.assertEqual(purple, blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(off,    blinkenlight1.light._color)
        self.assertEqual(green,  blinkenlight2.light._color)
        self.assertEqual(cyan,   blinkenlight3.light._color)
        self.advance_time_and_run(1)
        self.assertEqual(blue,   blinkenlight1.light._color)
        self.assertEqual(green,  blinkenlight2.light._color)
        self.assertEqual(purple, blinkenlight3.light._color)
