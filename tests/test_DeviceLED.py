from tests.MpfTestCase import MpfTestCase
from mpf.system.rgb_color import RGBColor, RGBColorCorrectionProfile


class TestDeviceLED(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/show_controller/'

    def get_platform(self):
        return 'smart_virtual'

    def testBasicOnAndOff(self):
        """Tests setting some LED colors (using default arguments)"""

        # Make sure hardware devices have been configured for tests
        self.assertIn('led_01', self.machine.leds)
        self.assertIn('led_02', self.machine.leds)

        self.advance_time_and_run(10)

        self.assertIsNone(self.machine.leds.led_01._color_correction_profile)
        self.assertIsNone(self.machine.leds.led_02._color_correction_profile)
        # TODO: Fix custom color correction profile
        #self.assertIsInstance(self.machine.leds['led_02']._color_correction_profile, RGBColorCorrectionProfile)

        # LEDs should start out off (current color is default RGBColor object)
        self.assertEqual(RGBColor(), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor(), self.machine.leds.led_02.state['color'])

        # --------------------------------------------------------
        # Set some LED colors (using default arguments)
        # --------------------------------------------------------
        self.machine.leds.led_01.color(RGBColor('SteelBlue'))
        self.assertEqual(RGBColor('SteelBlue'), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('SteelBlue'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(self.machine.clock.get_time(), self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(RGBColor('SteelBlue'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_01.state['priority'])
        self.machine.leds.led_02.color(RGBColor('006400'))
        self.assertEqual(RGBColor('006400'), self.machine.leds.led_02.state['color'])
        self.assertEqual(RGBColor('006400'), self.machine.leds.led_02.cache['color'])
        self.assertEqual(self.machine.clock.get_time(), self.machine.leds.led_02.cache['start_time'])
        self.assertEqual(RGBColor('006400'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_02.state['priority'])

        # Turn the LEDs off
        self.machine.leds.led_01.color(RGBColor('Off'))
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor((0, 0, 0)), self.machine.leds.led_01.cache['color'])
        self.assertEqual(self.machine.clock.get_time(), self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(RGBColor('Black'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_01.state['priority'])
        self.machine.leds.led_02.color(RGBColor('Off'))
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_02.state['color'])
        self.assertEqual(RGBColor((0, 0, 0)), self.machine.leds.led_02.cache['color'])
        self.assertEqual(self.machine.clock.get_time(), self.machine.leds.led_02.cache['start_time'])
        self.assertEqual(RGBColor('Black'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_02.state['priority'])

    def testOneSecondFadeUp(self):
        """One second fade from off (0, 0, 0) to white (255, 255, 255)"""

        # LED should start out off
        self.machine.leds.led_01.off()
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['color'])

        self.machine.leds.led_01.color(RGBColor('White'), fade_ms=1000)
        fade_start_time = self.machine.clock.get_time()
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(self.machine.clock.get_time(), self.machine.leds.led_01.state['start_time'])
        self.assertEqual(self.machine.clock.get_time() + 1, self.machine.leds.led_01.state['destination_time'])
        self.assertEqual(RGBColor('Black'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_01.state['priority'])
        self.assertIsNotNone(self.machine.leds.led_01.fade_task)
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['start_color'])
        self.assertEqual(fade_start_time, self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.leds.led_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

        self.machine_run()

        # Advance time 25% of the fade and check colors
        self.advance_time_and_run(0.25)
        self.assertEqual(RGBColor((63, 63, 63)), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(RGBColor((63, 63, 63)), self.machine.leds.led_01.hw_driver.current_color)

        # Check cache (should not have changed)
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['start_color'])
        self.assertEqual(fade_start_time, self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.leds.led_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

        # Advance time another 25% of the fade and check colors
        self.advance_time_and_run(0.25)
        self.assertEqual(RGBColor((127, 127, 127)), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(RGBColor((127, 127, 127)), self.machine.leds.led_01.hw_driver.current_color)

        # Check cache (should not have changed)
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['start_color'])
        self.assertEqual(fade_start_time, self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.leds.led_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

        # Advance time another 25% of the fade and check colors
        self.advance_time_and_run(0.25)
        self.assertEqual(RGBColor((191, 191, 191)), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(RGBColor((191, 191, 191)), self.machine.leds.led_01.hw_driver.current_color)

        # Check cache (should not have changed)
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['start_color'])
        self.assertEqual(fade_start_time, self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.leds.led_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

        # Advance time the last 25% of the fade and check colors (should be done)
        self.advance_time_and_run(0.25)
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.hw_driver.current_color)
        self.machine_run()
        self.assertIsNone(self.machine.leds.led_01.fade_task)

        # Check cache (should have been updated)
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(0, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

    def testInterruptFadeOut(self):
        """Interrupt (kill) a one second fade from white to off"""

        # LED should start out on (white)
        self.machine.leds.led_01.color(RGBColor('White'))
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['color'])

        self.machine.leds.led_01.color(RGBColor('Off'), fade_ms=1000)
        fade_start_time = self.machine.clock.get_time()
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['destination_color'])
        self.machine_run()

        # Advance time 50% of the fade and check colors
        self.advance_time_and_run(0.5)
        self.assertEqual(RGBColor((128, 128, 128)), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(RGBColor((128, 128, 128)), self.machine.leds.led_01.hw_driver.current_color)

        # Check cache (should not have changed)
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.cache['start_color'])
        self.assertEqual(fade_start_time, self.machine.leds.led_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.leds.led_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

        # Now interrupt the fade
        self.machine.leds.led_01._kill_fade()
        self.machine_run()

        # Fade should have been completed when killed
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['color'])
        self.assertEqual(RGBColor('White'), self.machine.leds.led_01.state['start_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.state['destination_color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertIsNone(self.machine.leds.led_01.fade_task)

        # Check cache (should have been updated)
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['color'])
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.cache['destination_color'])
        self.assertEqual(0, self.machine.leds.led_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.leds.led_01.cache['priority'])

        # TODO: Add priority/force and cache restore tests

