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

        # Make sure test LEDs have been configured
        self.assertIn('led_01', self.machine.leds)
        self.assertIn('led_02', self.machine.leds)

        # LEDs should start out off (current color is default RGBColor object)
        self.assertEqual(RGBColor(), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor(), self.machine.leds['led_02'].state['color'])

        # Start mode1 mode (should automatically start the test_show1 light show)
        self.machine.events.post('start_mode1')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertIn(self.machine.modes.mode1, self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show1'].running)

        # Check LEDs after first show step
        self.assertEqual(RGBColor(RGBColor.string_to_rgb('006400')), self.machine.leds['led_01'].state['color'])
        self.assertEqual(RGBColor(RGBColor.string_to_rgb('CCCCCC')), self.machine.leds['led_02'].state['color'])

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
