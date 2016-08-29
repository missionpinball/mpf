"""Test shows."""
import time

from unittest.mock import MagicMock

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestShows(MpfTestCase):
    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/shows/'

    def get_platform(self):
        return 'smart_virtual'

    def event_handler(self, **kwargs):
        pass

    def assertColorAlmostEqual(self, color1, color2, delta=6):
        if isinstance(color1, RGBColor) and isinstance(color2, RGBColor):
            difference = abs(color1.red - color2.red) +\
                abs(color1.blue - color2.blue) +\
                abs(color1.green - color2.green)
        else:
            difference = abs(color1[0] - color2[0]) +\
                abs(color1[1] - color2[1]) +\
                abs(color1[2] - color2[2])
        self.assertLessEqual(difference, delta, "Colors do not match: " + str(color1) + " " + str(color2))

    def test_default_shows(self):
        # test off
        show_on = self.machine.shows['off'].play(show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.1)
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        show_on.stop()
        self.advance_time_and_run(.1)
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)

        # test on
        show_off = self.machine.shows['on'].play(show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.1)
        self.assertEqual([255, 255, 255], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        show_off.stop()
        self.advance_time_and_run(.1)
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)

        # test flash
        # initially on
        show_flash = self.machine.shows['flash'].play(show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.1)
        self.assertEqual([255, 255, 255], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)

        # after 1s off
        self.advance_time_and_run(1)
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)

        # on after another 1s
        self.advance_time_and_run(1)
        self.assertEqual([255, 255, 255], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)

        show_flash.stop()
        self.advance_time_and_run(.1)
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)

        # test led_color
        show_led_color = self.machine.shows['led_color'].play(show_tokens=dict(leds='led_01', color="red"))
        self.advance_time_and_run(.1)
        self.assertEqual([255, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        show_led_color.stop()
        self.advance_time_and_run(.1)
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)

    def test_shows(self):
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
        self.assertIn('gi_01', self.machine.gis)
        self.assertIn('coil_01', self.machine.coils)
        self.assertIn('flasher_01', self.machine.flashers)

        # --------------------------------------------------------
        # test_show1 - Show with LEDs, lights, and GI
        # --------------------------------------------------------

        # LEDs should start out off (current color is default RGBColor object)
        self.assertEqual(list(RGBColor().rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(list(RGBColor().rgb),
                         self.machine.leds.led_02.hw_driver.current_color)

        # Lights should start out off (brightness is 0)
        self.assertEqual(0,
                         self.machine.lights.light_01.hw_driver
                         .current_brightness)
        self.assertEqual(0,
                         self.machine.lights.light_02.hw_driver
                         .current_brightness)

        # GI should start out enabled/on (brightness is 255)
        self.assertEqual(255,
                         self.machine.gis.gi_01.hw_driver.current_brightness)

        # Make sure all required shows are loaded
        start_time = time.time()
        while (not (self.machine.shows['test_show1'].loaded and
                    self.machine.shows['test_show2'].loaded and
                    self.machine.shows['test_show3'].loaded) and
                time.time() < start_time + 10):
            self.advance_time_and_run()

        self.assertTrue(self.machine.shows['test_show1'].loaded)
        self.assertEqual(self.machine.shows['test_show1'].total_steps, 5)

        # Start mode1 mode (should automatically start the test_show1 show)
        self.machine.events.post('start_mode1')
        self.advance_time_and_run(.2)
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(self.machine.modes.mode1.active)
        self.assertIn(self.machine.modes.mode1,
                      self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show1'].running)

        # Grab the running show instance
        running_show1 = [x for x in self.machine.shows['test_show1'].running if
                         x.name.startswith('test_show1')][0]
        self.assertIsNotNone(running_show1)

        # Make sure the show is running at the proper priority (of the mode)
        self.assertEqual(running_show1.priority, 200)

        # Check LEDs, lights, and GI after first show step
        self.assertEqual(list(RGBColor('006400').rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_01.stack[0]['priority'])
        self.assertEqual(list(RGBColor('CCCCCC').rgb),
                         self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_02.stack[0]['priority'])
        self.assertEqual(204, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(200, self.machine.lights.light_01.stack[0]['priority'])
        self.assertEqual(120, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(200, self.machine.lights.light_02.stack[0]['priority'])
        self.assertEqual(255, self.machine.gis.gi_01.hw_driver.current_brightness)

        # Check LEDs, lights, and GI after 2nd step
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('DarkGreen').rgb), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_01.stack[0]['priority'])

        self.assertEqual(list(RGBColor('Black').rgb), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_02.stack[0]['priority'])
        self.assertEqual(204, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(200, self.machine.lights.light_01.stack[0]['priority'])
        self.assertEqual(120, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(200, self.machine.lights.light_02.stack[0]['priority'])
        self.assertEqual(255, self.machine.gis.gi_01.hw_driver.current_brightness)

        # Check LEDs, lights, and GI after 3rd step
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('DarkSlateGray').rgb), self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_01.stack[0]['priority'])
        self.assertEqual(list(RGBColor('Tomato').rgb), self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_02.stack[0]['priority'])
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(200, self.machine.lights.light_01.stack[0]['priority'])
        self.assertEqual(51, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(200, self.machine.lights.light_02.stack[0]['priority'])
        self.assertEqual(153, self.machine.gis.gi_01.hw_driver.current_brightness)

        # Check LEDs, lights, and GI after 4th step (includes a fade to next
        #  color)
        self.advance_time_and_run()
        self.assertNotEqual(list(RGBColor('MidnightBlue').rgb),
                            self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_01.stack[0]['priority'])
        self.assertNotEqual(list(RGBColor('DarkOrange').rgb),
                            self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led_02.stack[0]['priority'])
        self.assertEqual(255,
                         self.machine.lights.light_01.hw_driver
                         .current_brightness)
        self.assertEqual(200, self.machine.lights.light_01.stack[0]['priority'])
        self.assertEqual(51,
                         self.machine.lights.light_02.hw_driver
                         .current_brightness)
        self.assertEqual(200, self.machine.lights.light_02.stack[0]['priority'])
        self.assertEqual(51,
                         self.machine.gis.gi_01.hw_driver.current_brightness)

        # Advance time so fade should have completed
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.assertEqual(list(RGBColor('MidnightBlue').rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(list(RGBColor('DarkOrange').rgb),
                         self.machine.leds.led_02.hw_driver.current_color)

        # Check LEDs after 5th step (includes a fade to black/off)
        self.advance_time_and_run(0.4)
        self.assertNotEqual(list(RGBColor('Off').rgb),
                            self.machine.leds.led_01.hw_driver.current_color)
        self.assertNotEqual(list(RGBColor('Off').rgb),
                            self.machine.leds.led_02.hw_driver.current_color)
        self.assertNotEqual(0,
                            self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertNotEqual(0,
                            self.machine.lights.light_02.hw_driver.current_brightness)

        # Advance time so fade should have completed
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.assertEqual(list(RGBColor('Off').rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(list(RGBColor('Off').rgb),
                         self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(0,
                         self.machine.lights.light_01.hw_driver
                         .current_brightness)
        self.assertEqual(0,
                         self.machine.lights.light_02.hw_driver
                         .current_brightness)
        self.assertEqual(0, self.machine.gis.gi_01.hw_driver.current_brightness)

        # Make sure show loops back to the first step
        self.advance_time_and_run(1.1)
        self.assertEqual(list(RGBColor('006400').rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(list(RGBColor('CCCCCC').rgb),
                         self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(204,
                         self.machine.lights.light_01.hw_driver
                         .current_brightness)
        self.assertEqual(120,
                         self.machine.lights.light_02.hw_driver
                         .current_brightness)
        self.assertEqual(255,
                         self.machine.gis.gi_01.hw_driver.current_brightness)

        # Stop the mode (and therefore the show)
        self.machine.events.post('stop_mode1')
        self.machine_run()
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(running_show1._stopped)
        self.assertFalse([x for x in self.machine.shows['test_show1'].running
                          if x.name.startswith('test_show1')])
        self.advance_time_and_run(5)

        # Make sure the lights and LEDs have reverted back to their prior
        # states from before the show started

        self.assertEqual(list(RGBColor().rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_01.stack[0]['priority'])
        self.assertEqual(list(RGBColor().rgb),
                         self.machine.leds.led_02.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led_02.stack[0]['priority'])
        self.assertEqual(0,
                         self.machine.lights.light_01.hw_driver
                         .current_brightness)
        self.assertEqual(0, self.machine.lights.light_01.stack[0]['priority'])
        self.assertEqual(0,
                         self.machine.lights.light_02.hw_driver
                         .current_brightness)
        self.assertEqual(0, self.machine.lights.light_02.stack[0]['priority'])
        self.assertEqual(0, self.machine.gis.gi_01.hw_driver.current_brightness)

        # --------------------------------------------------------
        # test_show2 - Show with events and triggers
        # --------------------------------------------------------

        # Setup callback for test_event event (fired in test show) and triggers
        self.event_handler = MagicMock()
        self.machine.events.add_handler('test_event', self.event_handler)
        self.machine.bcp.bcp_trigger = MagicMock()

        # Advance the clock enough to ensure the shows have time to load
        self.assertTrue(self.machine.shows['test_show2'].loaded)
        self.assertEqual(self.machine.shows['test_show2'].total_steps, 3)

        # Make sure our event callback and trigger have not been fired yet
        self.assertFalse(self.event_handler.called)
        self.assertFalse(self.machine.bcp.bcp_trigger.called)

        # Start the mode that will trigger playback of the test_show2 show
        self.machine.events.post('start_mode2')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertIn(self.machine.modes.mode2,
                      self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show2'].running)
        self.machine_run()

        # Make sure event callback and trigger have been called
        self.assertTrue(self.event_handler.called)
        self.assertTrue(self.machine.bcp.bcp_trigger)
        self.machine.bcp.bcp_trigger.assert_called_with('play_sound',
                                                        sound="test_1",
                                                        volume=0.5, loops=-1,
                                                        priority=0)

        # Advance to next show step and check for trigger
        self.advance_time_and_run()
        self.machine.bcp.bcp_trigger.assert_called_with('play_sound',
                                                        sound="test_2",
                                                        priority=0)

        # Advance to next show step and check for trigger
        self.advance_time_and_run()
        self.machine.bcp.bcp_trigger.assert_called_with('play_sound',
                                                        sound="test_3",
                                                        volume=0.35, loops=1,
                                                        priority=0)

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
        self.assertEqual(self.machine.shows['test_show3'].total_steps, 3)

        # Make sure our device callbacks have not been fired yet
        self.assertFalse(self.machine.coils['coil_01'].pulse.called)
        self.assertFalse(self.machine.flashers['flasher_01'].flash.called)

        # Start the mode that will trigger playback of the test_show3 show
        self.machine.events.post('start_mode3')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode3'))
        self.assertTrue(self.machine.modes.mode3.active)
        self.assertIn(self.machine.modes.mode3,
                      self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.shows['test_show3'].running)
        self.machine_run()

        # Make sure flasher device callback has been called (in first step
        # of show)
        self.assertTrue(self.machine.flashers['flasher_01'].flash.called)

        # Advance to next show step and check for coil firing
        self.advance_time_and_run()
        self.machine.coils['coil_01'].pulse.assert_called_with(power=1.0,
                                                               priority=0)

        # Advance to next show step and check for coil firing
        self.advance_time_and_run()
        self.machine.coils['coil_01'].pulse.assert_called_with(power=0.45,
                                                               priority=0)

        # TODO: Test device tags
        # TODO: Add test for multiple shows running at once with different
        # priorities
        # TODO: Test show playback rate

    def test_duration_in_shows(self):
        show = self.machine.shows['show_with_time_and_duration']
        self.assertEqual(6, len(show.show_steps))
        self.assertEqual(1, show.show_steps[0]['duration'])
        self.assertEqual(4, show.show_steps[1]['duration'])
        self.assertEqual(1, show.show_steps[2]['duration'])
        self.assertEqual(1, show.show_steps[3]['duration'])
        self.assertEqual(3, show.show_steps[4]['duration'])
        self.assertEqual(3, show.show_steps[5]['duration'])

    def test_tokens_in_shows(self):
        self.assertIn('leds_name_token', self.machine.shows)
        self.assertIn('leds_color_token', self.machine.shows)
        self.assertIn('leds_color_token_and_fade', self.machine.shows)
        self.assertIn('leds_extended', self.machine.shows)
        self.assertIn('lights_basic', self.machine.shows)
        self.assertIn('multiple_tokens', self.machine.shows)

        # test keys passed via method calls

        # test one LED
        show = self.machine.shows['leds_name_token'].play(
            show_tokens=dict(leds='led_01'))
        self.advance_time_and_run(.5)

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led_01.hw_driver.current_color)
        show.stop()

        # test passing tag instead of LED name
        self.machine.leds.led_01.clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_name_token'].play(show_tokens=dict(
            leds='tag1'))
        self.advance_time_and_run(.5)
        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color,
                         list(RGBColor('red').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color,
                         list(RGBColor('red').rgb))
        show.stop()

        # test passing multiple LEDs as string list
        self.machine.leds.led_01.clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_name_token'].play(show_tokens=dict(leds='led_01, led_02'))
        self.advance_time_and_run(.5)
        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color,
                         list(RGBColor('red').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color,
                         list(RGBColor('red').rgb))
        show.stop()

        # test passing color as a token
        self.machine.leds.led_01.clear_stack()
        self.machine.leds.led_02.clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_color_token'].play(
            show_tokens=dict(color1='blue', color2='green'))
        self.advance_time_and_run(2)
        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color,
                         list(RGBColor('blue').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color,
                         list(RGBColor('green').rgb))

        show.stop()

        # Test passing color as a token and include a fade string in express config
        show = self.machine.shows['leds_color_token_and_fade'].play(
            show_tokens=dict(color1='blue', color2='green'))
        self.advance_time_and_run(2)
        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color,
                         list(RGBColor('blue').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color,
                         list(RGBColor('green').rgb))

        show.stop()

        # test single LED in show with extended LED config
        self.machine.leds.led_01.clear_stack()
        self.machine.leds.led_02.clear_stack()
        self.advance_time_and_run()

        # led should be off
        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color,
                         [0, 0, 0])

        show = self.machine.shows['leds_extended'].play(
            show_tokens=dict(leds='led_01'))
        self.advance_time_and_run(.5)

        # show has fade of 1s, so after 0.5s it should be halfway to red
        # we use assertColorAlmostEqual because timing of shows + led fades is not stable in tests
        self.assertColorAlmostEqual(self.machine.leds.led_01.hw_driver.current_color, [127, 0, 0])
        show.stop()

        # test tag in show with extended LED config
        self.machine.leds.led_01.clear_stack()
        self.machine.leds.led_02.clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_extended'].play(
            show_tokens=dict(leds='tag1'))
        self.advance_time_and_run(.51)

        # show has fade of 1s, so after 0.5s it should be halfway to red
        # we use assertColorAlmostEqual because timing of shows + led fades is not stable in tests
        self.assertColorAlmostEqual(self.machine.leds.led_01.hw_driver.current_color, [127, 0, 0])
        self.assertColorAlmostEqual(self.machine.leds.led_02.hw_driver.current_color, [127, 0, 0])
        show.stop()

        # test single light in show
        show = self.machine.shows['lights_basic'].play(
            show_tokens=dict(lights='light_01'))
        self.advance_time_and_run(.5)

        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        show.stop()

        # test light tag in show
        self.machine.lights.light_01.off(force=True)
        self.advance_time_and_run()

        show = self.machine.shows['lights_basic'].play(
            show_tokens=dict(lights='tag1'))
        self.advance_time_and_run(.5)

        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.lights.light_02.hw_driver.current_brightness)
        show.stop()

        # test lights as string list in show
        self.machine.lights.light_01.off(force=True)
        self.advance_time_and_run()

        show = self.machine.shows['lights_basic'].play(
            show_tokens=dict(lights='light_01 light_02'))
        self.advance_time_and_run(.5)

        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.lights.light_02.hw_driver.current_brightness)
        show.stop()

        # test led and light tags in the same show
        self.machine.leds.led_01.clear_stack()
        self.machine.leds.led_02.clear_stack()
        self.machine.lights.light_01.off(force=True)
        self.machine.lights.light_02.off(force=True)
        self.advance_time_and_run()

        show = self.machine.shows['multiple_tokens'].play(
            show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.5)
        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color,
                         list(RGBColor('blue').rgb))
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        show.stop()
        self.advance_time_and_run(.5)

        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color, list(RGBColor('black').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color, list(RGBColor('black').rgb))

        self.post_event("play_show_assoc_tokens")
        self.advance_time_and_run(.5)

        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color, list(RGBColor('red').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color, list(RGBColor('red').rgb))

        self.post_event("stop_show_assoc_tokens")
        self.advance_time_and_run(.5)

        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color, list(RGBColor('black').rgb))
        self.assertEqual(self.machine.leds.led_02.hw_driver.current_color, list(RGBColor('black').rgb))

        self.post_event("test_mode_started")
        self.advance_time_and_run(.5)

        self.assertEqual(self.machine.leds.led_01.hw_driver.current_color, list(RGBColor('red').rgb))
        self.post_event("test_mode_stopped")

    def test_get_show_copy(self):
        copied_show = self.machine.shows['test_show1'].get_show_steps()
        self.assertEqual(5, len(copied_show))
        self.assertIs(type(copied_show), list)
        self.assertEqual(copied_show[0]['duration'], 1.0)
        self.assertEqual(copied_show[1]['duration'], 1.0)
        self.assertEqual(copied_show[2]['duration'], 1.0)
        self.assertEqual(copied_show[4]['duration'], 2.0)
        self.assertIn(self.machine.leds.led_01, copied_show[0]['leds'])
        self.assertIn(self.machine.leds.led_02, copied_show[0]['leds'])
        self.assertEqual(copied_show[0]['leds'][self.machine.leds.led_01],
                         dict(color='006400', fade_ms=0, priority=0))
        self.assertEqual(copied_show[0]['leds'][self.machine.leds.led_02],
                         dict(color='cccccc', fade_ms=0, priority=0))
        self.assertEqual(copied_show[3]['leds'][self.machine.leds.led_01],
                         dict(color='midnightblue', fade_ms=500, priority=0))

    def _stop_shows(self):
        while self.machine.show_controller.running_shows:
            for show in self.machine.show_controller.running_shows:
                show.stop()
                self.advance_time_and_run()
        self.assertFalse(self.machine.show_controller.running_shows)

    def test_show_player(self):
        # Basic show
        self.machine.events.post('play_test_show1')
        self.advance_time_and_run()
        self.assertEqual(1, len(self.machine.show_controller.get_running_shows(
                         'test_show1')))
        self._stop_shows()

        # Test priority
        self.machine.events.post('play_with_priority')
        self.advance_time_and_run()
        self.assertEqual(15, self.machine.show_controller.running_shows[0].priority)
        self._stop_shows()

        # Test speed
        self.machine.events.post('play_with_speed')
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.show_controller.running_shows[0].speed)
        self._stop_shows()

        # Test start step
        self.machine.events.post('play_with_start_step')
        self.advance_time_and_run(.1)
        self.assertEqual(2, self.machine.show_controller.running_shows[0].next_step_index)
        self._stop_shows()

        # Test start step
        self.machine.events.post('play_with_neg_start_step')
        self.advance_time_and_run(.1)
        self.assertEqual(4, self.machine.show_controller.running_shows[0].next_step_index)
        self._stop_shows()

        # Test loops
        self.machine.events.post('play_with_loops')
        self.advance_time_and_run(.1)
        self.assertEqual(2, self.machine.show_controller.running_shows[0].loops)
        self._stop_shows()

        # Test sync_ms 1000ms
        self.machine.events.post('play_with_sync_ms_1000')
        self.advance_time_and_run(.1)

        # should be 0 +/- the duration of a frame

        self.assertAlmostEqual(0.0, self.machine.show_controller.running_shows[0].next_step_time % 1.0, delta=(1 / 30))
        self._stop_shows()

        # Test sync_ms 500ms
        self.machine.events.post('play_with_sync_ms_500')
        self.advance_time_and_run(.1)
        self.assertAlmostEqual(0.0, self.machine.show_controller.running_shows[0].next_step_time % 0.5, delta=(1 / 30))
        self._stop_shows()

        # Test manual advance
        self.machine.events.post('play_with_manual_advance')
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.show_controller.running_shows[0].next_step_index)

    def test_pause_resume_shows(self):
        self.machine.events.post('play_test_show1')
        # make sure show is advancing
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.show_controller.running_shows[0].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_controller.running_shows[0].next_step_index)

        self.machine.events.post('pause_test_show1')

        # make sure show stops advancing
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_controller.running_shows[0].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_controller.running_shows[0].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_controller.running_shows[0].next_step_index)

        # make sure show starts advanving again
        self.machine.events.post('resume_test_show1')
        self.advance_time_and_run(0.1)
        self.assertEqual(4, self.machine.show_controller.running_shows[0].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(5, self.machine.show_controller.running_shows[0].next_step_index)
        self.advance_time_and_run(2)
        self.assertEqual(1, self.machine.show_controller.running_shows[0].next_step_index)

    def test_show_from_mode_config(self):
        self.assertIn('show_from_mode', self.machine.shows)

        self.assertEqual(1, len(self.machine.shows['show_from_mode'].show_steps))

    def test_too_many_tokens(self):
        with self.assertRaises(ValueError):
            self.machine.shows['lights_basic'].play(show_tokens=dict(
                lights='light_01', fake='foo'))

    def test_too_few_tokens(self):
        self.machine.shows['multiple_tokens'].play(show_tokens=dict(
            lights='light_01'))

    def test_keys_in_show_player(self):
        self.post_event("play_on_led1")
        self.advance_time_and_run()
        self.assertEqual([255, 255, 255], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual([0, 0, 0], self.machine.leds.led_02.hw_driver.current_color)

        self.post_event("play_on_led2")
        self.advance_time_and_run()
        self.assertEqual([255, 255, 255], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual([255, 255, 255], self.machine.leds.led_02.hw_driver.current_color)

        self.post_event("stop_on_led1")
        self.advance_time_and_run()
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual([255, 255, 255], self.machine.leds.led_02.hw_driver.current_color)

        self.post_event("stop_on_led2")
        self.advance_time_and_run()
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.assertEqual([0, 0, 0], self.machine.leds.led_02.hw_driver.current_color)

    def test_nested_shows(self):
        self.mock_event("test")
        self.assertFalse(self.machine.shows['mychildshow'].loaded)
        show = self.machine.shows['myparentshow'].play(loops=0)

        self.advance_time_and_run(5)
        while not self.machine.shows['mychildshow'].loaded:
            self.advance_time_and_run(1)

        self.advance_time_and_run(1)
        self.assertEqual(1, self._events['test'])
        self.assertTrue(self.machine.shows['mychildshow'].loaded)
        show.stop()

    def test_nested_shows_stop_before_load(self):
        self.mock_event("test")
        self.assertFalse(self.machine.shows['mychildshow'].loaded)
        show = self.machine.shows['myparentshow'].play(loops=0)
        show.stop()
        self.assertEqual(0, self._events['test'])

        self.advance_time_and_run(5)
        while not self.machine.shows['mychildshow'].loaded:
            self.advance_time_and_run(1)
        self.assertEqual(0, self._events['test'])
        self.assertTrue(self.machine.shows['mychildshow'].loaded)

    def test_manual_advance(self):
        self.assertEqual([0, 0, 0], self.machine.leds.led_01.hw_driver.current_color)
        self.post_event("play_manual_advance")
        self.advance_time_and_run()
        self.assertEqual([255, 0, 0], self.machine.leds.led_01.hw_driver.current_color)

        self.post_event("advance_manual_advance")
        self.advance_time_and_run()
        self.assertEqual([0, 255, 0], self.machine.leds.led_01.hw_driver.current_color)

        self.post_event("advance_manual_advance")
        self.advance_time_and_run()
        self.assertEqual([0, 0, 255], self.machine.leds.led_01.hw_driver.current_color)

        self.post_event("advance_manual_step_back")
        self.advance_time_and_run()
        self.assertEqual([0, 255, 0], self.machine.leds.led_01.hw_driver.current_color)

        self.post_event("advance_manual_advance")
        self.advance_time_and_run()
        self.assertEqual([0, 0, 255], self.machine.leds.led_01.hw_driver.current_color)

        self.post_event("play_manual_advance")
        self.advance_time_and_run()
        self.assertEqual([255, 0, 0], self.machine.leds.led_01.hw_driver.current_color)

        # test wrap around
        self.post_event("advance_manual_step_back")
        self.advance_time_and_run()
        self.assertEqual([0, 0, 255], self.machine.leds.led_01.hw_driver.current_color)