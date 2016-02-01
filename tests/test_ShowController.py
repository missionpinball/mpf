from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
from mpf.system.rgb_color import RGBColor


class TestShowController(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/show_controller/'

    def get_platform(self):
        return 'smart_virtual'

    def event_handler(self, **kwargs):
        pass

    def testShows(self):
        # Make sure required modes have been loaded
        self.assertIn('mode1', self.machine.modes)
        self.assertIn('mode2', self.machine.modes)
        self.assertIn('mode3', self.machine.modes)

        # Make sure test shows exist and can be loaded
        self.assertIn('test_show1', self.machine.shows)
        self.assertIn('test_show2', self.machine.shows)
        self.assertIn('test_show3', self.machine.shows)

        # Make sure hardware devices have been configured for tests
        self.assertIn('led_01', self.machine.leds)
        self.assertIn('led_02', self.machine.leds)
        self.assertIn('light_01', self.machine.lights)
        self.assertIn('light_02', self.machine.lights)
        self.assertIn('gi_01', self.machine.gi)
        self.assertIn('coil_01', self.machine.coils)
        self.assertIn('flasher_01', self.machine.flashers)

        # --------------------------------------------------------
        # test_show1 - Show with LEDs, lights, and GI
        # --------------------------------------------------------

        # LEDs should start out off (current color is default RGBColor object)
        self.assertEqual(RGBColor(), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor(), self.machine.leds.led_02.hw_driver.current_color)

        # Lights should start out off (brightness is 0)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_02.hw_driver.current_brightness)

        # GI should start out enabled/on (brightness is 255)
        self.assertEqual(255, self.machine.gi.gi_01.hw_driver.current_brightness)

        # Make sure all required shows are loaded
        start_time = self.machine.clock.get_time()
        while (not (self.machine.shows['test_show1'].loaded and
                self.machine.shows['test_show2'].loaded and
                self.machine.shows['test_show3'].loaded) and 
                self.machine.clock.get_time() < start_time + 100000):
            self.advance_time(0.001)

        self.assertTrue(self.machine.shows['test_show1'].loaded)
        self.assertEqual(self.machine.shows['test_show1'].total_steps, 6)

        # Start mode1 mode (should automatically start the test_show1 show)
        self.machine.events.post('start_mode1')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertIn(self.machine.modes.mode1, self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show1'].running)

        # Check LEDs, lights, and GI after first show step
        self.machine_run()
        self.assertEqual(RGBColor('006400'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor('CCCCCC'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(204, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(120, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.gi.gi_01.hw_driver.current_brightness)

        # Check LEDs, lights, and GI after 2nd step
        self.advance_time_and_run(1.0)
        self.assertEqual(RGBColor('DarkGreen'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor('Black'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(204, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(120, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.gi.gi_01.hw_driver.current_brightness)

        # Check LEDs, lights, and GI after 3rd step
        self.advance_time_and_run(1.0)
        self.assertEqual(RGBColor('DarkSlateGray'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor('Tomato'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(51, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(153, self.machine.gi.gi_01.hw_driver.current_brightness)

        # Check LEDs, lights, and GI after 4th step (includes a fade to next color)
        self.advance_time_and_run(1.0)
        self.assertNotEqual(RGBColor('MidnightBlue'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertNotEqual(RGBColor('DarkOrange'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(51, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(51, self.machine.gi.gi_01.hw_driver.current_brightness)

        # Advance time so fade should have completed
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.assertEqual(RGBColor('MidnightBlue'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor('DarkOrange'), self.machine.leds.led_02.hw_driver.current_color)

        # Check LEDs after 5th step (includes a fade to black/off)
        self.advance_time_and_run(0.4)
        self.assertNotEqual(RGBColor('Off'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertNotEqual(RGBColor('Off'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertNotEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertNotEqual(0, self.machine.lights.light_02.hw_driver.current_brightness)

        # Advance time so fade should have completed
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor('Off'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.gi.gi_01.hw_driver.current_brightness)

        # Make sure show loops back to the first step
        self.advance_time_and_run(1.1)
        self.assertEqual(RGBColor('006400'), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(RGBColor('CCCCCC'), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(204, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(120, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.gi.gi_01.hw_driver.current_brightness)

        # TODO: Add tests for reset and hold

        # Stop the mode (and therefore the show)
        self.machine.events.post('stop_mode1')
        self.machine_run()
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.advance_time_and_run(5)

        # --------------------------------------------------------
        # test_show2 - Show with events and triggers
        # --------------------------------------------------------

        # Setup callback for test_event event (fired in test show) and triggers
        self.event_handler = MagicMock()
        self.machine.events.add_handler('test_event', self.event_handler)
        self.machine.bcp.bcp_trigger = MagicMock()

        # Advance the clock enough to ensure the shows have time to load
        self.assertTrue(self.machine.shows['test_show2'].loaded)
        self.assertEqual(self.machine.shows['test_show2'].total_steps, 4)

        # Make sure our event callback and trigger have not been fired yet
        self.assertFalse(self.event_handler.called)
        self.assertFalse(self.machine.bcp.bcp_trigger.called)

        # Start the mode that will trigger playback of the test_show2 show
        self.machine.events.post('start_mode2')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertIn(self.machine.modes.mode2, self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show2'].running)
        self.machine_run()

        # Make sure event callback and trigger have been called
        self.assertTrue(self.event_handler.called)
        self.assertTrue(self.machine.bcp.bcp_trigger)
        self.machine.bcp.bcp_trigger.assert_called_with('play_sound', sound="test_1", volume=0.5, loops=-1)

        # Advance to next show step and check for trigger
        self.advance_time_and_run(1.0)
        self.machine.bcp.bcp_trigger.assert_called_with('play_sound', sound="test_2")

        # Advance to next show step and check for trigger
        self.advance_time_and_run(1.0)
        self.machine.bcp.bcp_trigger.assert_called_with('play_sound', sound="test_3", volume=0.35, loops=1)

        # Stop the mode (and therefore the show)
        self.machine.events.post('stop_mode2')
        self.machine_run()
        self.assertFalse(self.machine.mode_controller.is_active('mode2'))
        self.advance_time_and_run(5)

        # --------------------------------------------------------
        # test_show3 - Show with coils and flashers
        # --------------------------------------------------------

        # Setup callback for test_event event (fired in test show) and triggers
        self.machine.coils['coil_01'].pulse = MagicMock()
        self.machine.flashers['flasher_01'].flash = MagicMock()

        self.assertTrue(self.machine.shows['test_show3'].loaded)
        self.assertEqual(self.machine.shows['test_show3'].total_steps, 4)

        # Make sure our device callbacks have not been fired yet
        self.assertFalse(self.machine.coils['coil_01'].pulse.called)
        self.assertFalse(self.machine.flashers['flasher_01'].flash.called)

        # Start the mode that will trigger playback of the test_show3 show
        self.machine.events.post('start_mode3')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode3'))
        self.assertTrue(self.machine.modes.mode3.active)
        self.assertIn(self.machine.modes.mode3, self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show3'].running)
        self.machine_run()

        # Make sure flasher device callback has been called (in first step of show)
        self.assertTrue(self.machine.flashers['flasher_01'].flash.called)

        # Advance to next show step and check for coil firing
        self.advance_time_and_run(1.0)
        self.machine.coils['coil_01'].pulse.assert_called_with(power=1.0)

        # Advance to next show step and check for coil firing
        self.advance_time_and_run(1.0)
        self.machine.coils['coil_01'].pulse.assert_called_with(power=0.45)

    # TODO: Test device tags
    # TODO: Add test for multiple shows running at once with different priorities
    # TODO: Test show playback rate

