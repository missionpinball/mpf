from tests.MpfTestCase import MpfTestCase
from mpf.system.rgb_color import RGBColor


class TestShowController(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/show_controller/'

    def get_platform(self):
        return 'smart_virtual'

    def testSimpleLEDShow(self):
        # Make sure attract mode has been loaded
        self.assertIn('mode1', self.machine.modes)

        # Make sure test_show1 exists and can be loaded
        self.assertIn('test_show1', self.machine.shows)
        self.assertTrue(self.machine.shows['test_show1'].loaded)
        self.assertEqual(self.machine.shows['test_show1'].total_steps, 6)

        # Make sure test LEDs have been configured
        self.assertIn('led_01', self.machine.leds)
        self.assertIn('led_02', self.machine.leds)

        # LEDs should start out off (current color is default RGBColor object)
        self.assertEqual(RGBColor(), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor(), self.machine.leds['led_02'].state['color'])

        # Advance the clock enough to ensure the shows have time to load
        self.advance_time_and_run(2)

        # Start mode1 mode (should automatically start the test_show1 light show)
        self.machine.events.post('start_mode1')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertIn(self.machine.modes.mode1, self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show1'].running)

        # Check LEDs after first show step
        self.machine_run()
        self.assertEqual(RGBColor('006400'), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor('CCCCCC'), self.machine.leds['led_02'].state['color'])

        # Check LEDs after 2nd step
        self.advance_time_and_run(1.0)
        self.assertEqual(RGBColor('DarkGreen'), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor('Black'), self.machine.leds['led_02'].state['color'])

        # Check LEDs after 3rd step
        self.advance_time_and_run(1.0)
        self.assertEqual(RGBColor('DarkSlateGray'), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor('Tomato'), self.machine.leds['led_02'].state['color'])

        # Check LEDs after 4th step (includes a fade to next color)
        self.advance_time_and_run(1.0)
        self.assertNotEqual(RGBColor('MidnightBlue'), self.machine.leds['led_01'].state['color'])
        self.assertNotEqual(RGBColor('DarkOrange'), self.machine.leds['led_02'].state['color'])

        # Advance time so fade should have completed
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.assertEqual(RGBColor('MidnightBlue'), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor('DarkOrange'), self.machine.leds['led_02'].state['color'])

        # Check LEDs after 5th step (includes a fade to black/off)
        self.advance_time_and_run(0.4)
        self.assertNotEqual(RGBColor('Off'), self.machine.leds['led_01'].state['color'])
        self.assertNotEqual(RGBColor('Off'), self.machine.leds['led_02'].state['color'])

        # Advance time so fade should have completed
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.assertEqual(RGBColor('Off'), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds['led_02'].state['color'])

        # Make sure show loops back to the first step
        self.advance_time_and_run(1.1)
        self.assertEqual(RGBColor('006400'), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor('CCCCCC'), self.machine.leds['led_02'].state['color'])

    def testShowTriggers(self):
        self.assertIn('mode2', self.machine.modes)

        # Make sure test_show1 exists and can be loaded
        self.assertIn('test_show_triggers', self.machine.shows)

        self.machine.events.post('start_mode2')
        self.advance_time_and_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertIn(self.machine.modes.mode2, self.machine.mode_controller.active_modes)

        self.assertTrue(self.machine.shows['test_show_triggers'].running)
