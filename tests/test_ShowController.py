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
        self.assertIn('attract', self.machine.modes)

        # Make sure test_show1 exists and can be loaded
        self.assertIn('test_show1', self.machine.shows)

        # Make sure test LEDs have been configured
        self.assertIn('led_01', self.machine.leds)
        self.assertIn('led_02', self.machine.leds)

        # LEDs should start out off (current color is default RGBColor object)
        self.assertEqual(RGBColor(), self.machine.leds['led_01'].current_color)
        self.assertEqual(RGBColor(), self.machine.leds['led_02'].current_color)

        # Start attract mode (should automatically start the test_show1 light show)
        self.machine.events.post('start_attract')
        self.advance_time_and_run()

