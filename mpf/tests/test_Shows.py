"""Test shows."""
import time

from unittest.mock import MagicMock

from mpf.platforms.interfaces.driver_platform_interface import PulseSettings
from mpf.tests.MpfTestCase import MpfTestCase, test_config


class TestShows(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/shows/'

    def get_platform(self):
        return 'smart_virtual'

    def event_handler(self, **kwargs):
        pass

    def test_default_shows(self):
        # test off
        show_off = self.machine.shows['off'].play(show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightChannel("light_01", 0)
        show_off.stop()
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightChannel("light_01", 0)

        # test on
        show_on = self.machine.shows['on'].play(show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [255, 255, 255])
        self.assertLightChannel("light_01", 255)
        show_on.stop()
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightChannel("light_01", 0)

        # test flash
        # initially on
        show_flash = self.machine.shows['flash'].play(show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [255, 255, 255])
        self.assertLightChannel("light_01", 255)

        # after 1s off
        self.advance_time_and_run(1)
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightChannel("light_01", 0)

        # on after another 1s
        self.advance_time_and_run(1)
        self.assertLightColor("led_01", [255, 255, 255])
        self.assertLightChannel("light_01", 255)

        show_flash.stop()
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightChannel("light_01", 0)

        # test led_color
        show_led_color = self.machine.shows['led_color'].play(show_tokens=dict(leds='led_01', color="red"))
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [255, 0, 0])
        show_led_color.stop()
        self.advance_time_and_run(.1)
        self.assertLightColor("led_01", [0, 0, 0])

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
        self.assertIn('led_01', self.machine.lights)
        self.assertIn('led_02', self.machine.lights)
        self.assertIn('light_01', self.machine.lights)
        self.assertIn('light_02', self.machine.lights)
        self.assertIn('gi_01', self.machine.lights)
        self.assertIn('coil_01', self.machine.coils)
        self.assertIn('flasher_01', self.machine.lights)

        # --------------------------------------------------------
        # test_show1 - Show with LEDs, lights, and GI
        # --------------------------------------------------------

        # LEDs should start out off (current color is default RGBColor object)
        self.assertLightColor("led_01", "off")
        self.assertLightColor("led_02", "off")

        # Lights should start out off (brightness is 0)
        self.assertLightChannel("light_01", 0)
        self.assertLightChannel("light_02", 0)

        # GI should start out disabled
        self.assertLightChannel("gi_01", 0)

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
        self.assertTrue(self.machine.modes["mode1"].active)
        self.assertIn(self.machine.modes["mode1"],
                      self.machine.mode_controller.active_modes)

        # Grab the running show instance
        running_show1 = self.machine.show_player.instances['mode1']['show_player']['test_show1']
        self.assertIsNotNone(running_show1)

        # Make sure the show is running at the proper priority (of the mode)
        self.assertEqual(running_show1.show_config.priority, 200)

        # Check LEDs, lights, and GI after first show step
        self.assertLightColor("led_01", '006400')
        self.assertEqual(200, self.machine.lights["led_01"].stack[0].priority)
        self.assertLightColor("led_02", 'CCCCCC')
        self.assertEqual(200, self.machine.lights["led_02"].stack[0].priority)
        self.assertLightChannel("light_01", 204)
        self.assertEqual(200, self.machine.lights["light_01"].stack[0].priority)
        self.assertLightChannel("light_02", 120)
        self.assertEqual(200, self.machine.lights["light_02"].stack[0].priority)
        self.assertLightChannel("gi_01", 255)

        # Check LEDs, lights, and GI after 2nd step
        self.advance_time_and_run()
        self.assertLightColor("led_01", 'DarkGreen')
        self.assertEqual(200, self.machine.lights["led_01"].stack[0].priority)

        self.assertLightColor("led_02", 'Black')
        self.assertEqual(200, self.machine.lights["led_02"].stack[0].priority)
        self.assertLightChannel("light_01", 204)
        self.assertEqual(200, self.machine.lights["light_01"].stack[0].priority)
        self.assertLightChannel("light_02", 120)
        self.assertEqual(200, self.machine.lights["light_02"].stack[0].priority)
        self.assertLightChannel("gi_01", 255)

        # Check LEDs, lights, and GI after 3rd step
        self.advance_time_and_run()
        self.assertLightColor("led_01", 'DarkSlateGray')
        self.assertEqual(200, self.machine.lights["led_01"].stack[0].priority)
        self.assertLightColor("led_02", 'Tomato')
        self.assertEqual(200, self.machine.lights["led_02"].stack[0].priority)
        self.assertLightChannel("light_01", 255)
        self.assertEqual(200, self.machine.lights["light_01"].stack[0].priority)
        self.assertLightChannel("light_02", 51)
        self.assertEqual(200, self.machine.lights["light_02"].stack[0].priority)
        self.assertLightChannel("gi_01", 153)

        # Check LEDs, lights, and GI after 4th step (includes a fade to next
        #  color)
        self.advance_time_and_run()
        self.assertNotLightColor("led_01", 'MidnightBlue')
        self.assertEqual(200, self.machine.lights["led_01"].stack[0].priority)
        self.assertNotLightColor("led_02", 'DarkOrange')
        self.assertEqual(200, self.machine.lights["led_02"].stack[0].priority)
        self.assertLightChannel("light_01", 255)
        self.assertEqual(200, self.machine.lights["light_01"].stack[0].priority)
        self.assertLightChannel("light_02", 51)
        self.assertEqual(200, self.machine.lights["light_02"].stack[0].priority)
        self.assertLightChannel("gi_01", 51)

        # Advance time so fade should have completed
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.advance_time_and_run(0.1)
        self.assertLightColor("led_01", 'MidnightBlue')
        self.assertLightColor("led_02", 'DarkOrange')

        # Check LEDs after 5th step (includes a fade to black/off)
        self.advance_time_and_run(0.4)
        self.assertNotLightColor("led_01", 'Off')
        self.assertNotLightColor("led_02", 'Off')
        self.assertNotLightChannel("light_01", 0)
        self.assertNotLightChannel("light_02", 0)

        # Advance time so fade should have completed
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.advance_time_and_run(0.2)
        self.assertLightColor("led_01", 'Off')
        self.assertLightColor("led_02", 'Off')
        self.assertLightChannel("light_01", 0)
        self.assertLightChannel("light_02", 0)
        self.assertLightChannel("gi_01", 0)

        # Make sure show loops back to the first step
        self.advance_time_and_run(1.1)
        self.assertLightColor("led_01", '006400')
        self.assertLightColor("led_02", 'CCCCCC')
        self.assertLightChannel("light_01", 204)
        self.assertLightChannel("light_02", 120)
        self.assertLightChannel("gi_01", 255)

        self.assertNotIn("show_from_mode", self.machine.show_player.instances['mode1']['show_player'])
        self.machine.set_machine_var("test", 42)
        self.advance_time_and_run(.01)
        self.assertTrue(self.machine.show_player.instances['mode1']['show_player']['show_from_mode'])

        # Stop the mode (and therefore the show)
        self.machine.events.post('stop_mode1')
        self.machine_run()
        self.assertNotIn("show_from_mode", self.machine.show_player.instances['mode1']['show_player'])
        self.assertFalse(self.machine.mode_controller.is_active('mode1'))
        self.assertTrue(running_show1._stopped)
        self.assertNotIn("test_show1", self.machine.show_player.instances['mode1']['show_player'])
        self.advance_time_and_run(5)

        # Make sure the lights and LEDs have reverted back to their prior
        # states from before the show started

        self.assertLightColor("led_01", "off")
        self.assertFalse(self.machine.lights["led_01"].stack)
        self.assertLightColor("led_01", "off")
        self.assertFalse(self.machine.lights["led_02"].stack)
        self.assertLightChannel("light_01", 0)
        self.assertFalse(self.machine.lights["light_01"].stack)
        self.assertLightChannel("light_02", 0)
        self.assertFalse(self.machine.lights["light_02"].stack)
        self.assertLightChannel("gi_01", 0)

        # --------------------------------------------------------
        # test_show2 - Show with events
        # --------------------------------------------------------

        # Setup callback for test_event event (fired in test show) and triggers
        self.event_handler = MagicMock()
        self.event_handler_2 = MagicMock()
        self.machine.events.add_handler('test_event', self.event_handler)
        self.machine.events.add_handler('play_sound', self.event_handler_2)

        # Advance the clock enough to ensure the shows have time to load
        self.assertTrue(self.machine.shows['test_show2'].loaded)
        self.assertEqual(self.machine.shows['test_show2'].total_steps, 3)

        # Make sure our event callbacks have not been fired yet
        self.assertFalse(self.event_handler.called)
        self.assertFalse(self.event_handler_2.called)

        # Start the mode that will trigger playback of the test_show2 show
        self.machine.events.post('start_mode2')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))
        self.assertTrue(self.machine.modes["mode2"].active)
        self.assertIn(self.machine.modes["mode2"],
                      self.machine.mode_controller.active_modes)
        self.assertTrue(self.machine.show_player.instances['mode2']['show_player']['test_show2'])
        self.machine_run()

        # Make sure event callbacks have been called
        self.assertTrue(self.event_handler.called)
        self.assertTrue(self.event_handler_2.called)
        self.event_handler_2.assert_called_with(priority=0,
                                                sound="test_1",
                                                loops=-1,
                                                volume=0.5)

        # Advance to next show step and check for event
        self.advance_time_and_run()
        self.event_handler_2.assert_called_with(priority=0,
                                                sound="test_2")

        # Advance to next show step and check for event
        self.advance_time_and_run()
        self.event_handler_2.assert_called_with(priority=0,
                                                sound="test_3",
                                                loops=1,
                                                volume=0.35)

        # Stop the mode (and therefore the show)
        self.machine.events.post('stop_mode2')
        self.machine_run()
        self.assertFalse(self.machine.mode_controller.is_active('mode2'))
        self.advance_time_and_run(5)

        # --------------------------------------------------------
        # test_show3 - Show with coils and flashers
        # --------------------------------------------------------

        # Setup callback for test_event event (fired in test show) and triggers
        self.machine.coils['coil_01'].hw_driver.pulse = MagicMock()
        self.machine.coils['flasher_01'].hw_driver.enable = MagicMock()

        self.assertTrue(self.machine.shows['test_show3'].loaded)
        self.assertEqual(self.machine.shows['test_show3'].total_steps, 3)

        # Make sure our device callbacks have not been fired yet
        self.assertFalse(self.machine.coils['coil_01'].hw_driver.pulse.called)
        self.assertFalse(self.machine.coils['flasher_01'].hw_driver.enable.called)

        # Start the mode that will trigger playback of the test_show3 show
        self.machine.events.post('start_mode3')
        self.machine_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode3'))
        self.assertTrue(self.machine.modes["mode3"].active)
        self.assertIn(self.machine.modes["mode3"],
                      self.machine.mode_controller.active_modes)
        self.machine.show_player.instances['mode3']['show_player']['test_show3']
        self.machine_run()

        # Make sure flasher device callback has been called (in first step
        # of show)
        self.advance_time_and_run(.01)
        self.assertTrue(self.machine.coils['flasher_01'].hw_driver.enable.called)

        # Advance to next show step and check for coil firing
        self.advance_time_and_run()
        self.machine.coils['coil_01'].hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=30))

        # Advance to next show step and check for coil firing
        self.advance_time_and_run()
        self.machine.coils['coil_01'].hw_driver.pulse.assert_called_with(PulseSettings(power=0.45, duration=30))

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

        self.assertLightColor("led_01", 'red')
        show.stop()

        # test passing tag instead of LED name
        self.machine.lights["led_01"].clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_name_token'].play(show_tokens=dict(
            leds='tag1'))
        self.advance_time_and_run(.5)
        self.assertLightColor("led_01", 'red')
        self.assertLightColor("led_02", 'red')
        show.stop()

        # test passing multiple LEDs as string list
        self.machine.lights["led_01"].clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_name_token'].play(show_tokens=dict(leds='led_01, led_02'))
        self.advance_time_and_run(.5)
        self.assertLightColor("led_01", 'red')
        self.assertLightColor("led_02", 'red')
        show.stop()

        # test passing color as a token
        self.machine.lights["led_01"].clear_stack()
        self.machine.lights["led_02"].clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_color_token'].play(
            show_tokens=dict(color1='blue', color2='green'))
        self.advance_time_and_run(2)
        self.assertLightColor("led_01", 'blue')
        self.assertLightColor("led_02", 'green')

        show.stop()

        # Test passing color as a token and include a fade string in express config
        show = self.machine.shows['leds_color_token_and_fade'].play(
            show_tokens=dict(color1='blue', color2='green'))
        self.advance_time_and_run(2)
        self.assertLightColor("led_01", 'blue')
        self.assertLightColor("led_02", 'green')

        show.stop()

        # test single LED in show with extended LED config
        self.machine.lights["led_01"].clear_stack()
        self.machine.lights["led_02"].clear_stack()
        self.advance_time_and_run()

        # led should be off
        self.assertLightColor("led_01", [0, 0, 0])

        show = self.machine.shows['leds_extended'].play(
            show_tokens=dict(leds='led_01'))
        self.advance_time_and_run(.5)

        # show has fade of 1s, so after 0.5s it should be halfway to red
        # we use assertColorAlmostEqual because timing of shows + led fades is not stable in tests
        #self.assertColorAlmostEqual(self.machine.leds.led_01.hw_driver.current_color, [127, 0, 0])
        show.stop()

        # test tag in show with extended LED config
        self.machine.lights["led_01"].clear_stack()
        self.machine.lights["led_02"].clear_stack()
        self.advance_time_and_run()

        show = self.machine.shows['leds_extended'].play(
            show_tokens=dict(leds='tag1'))
        self.advance_time_and_run(.51)

        # show has fade of 1s, so after 0.5s it should be halfway to red
        # we use assertColorAlmostEqual because timing of shows + led fades is not stable in tests
        #self.assertColorAlmostEqual(self.machine.leds.led_01.hw_driver.current_color, [127, 0, 0])
        #self.assertColorAlmostEqual(self.machine.leds.led_02.hw_driver.current_color, [127, 0, 0])
        show.stop()

        # test single light in show
        show = self.machine.shows['lights_basic'].play(
            show_tokens=dict(lights='light_01'))
        self.advance_time_and_run(.5)

        self.assertLightChannel("light_01", 255)
        show.stop()

        # test light tag in show
        self.machine.lights["light_01"].off(force=True)
        self.advance_time_and_run()

        show = self.machine.shows['lights_basic'].play(
            show_tokens=dict(lights='tag1'))
        self.advance_time_and_run(.5)

        self.assertLightChannel("light_01", 255)
        self.assertLightChannel("light_02", 255)
        show.stop()

        # test lights as string list in show
        self.machine.lights["light_01"].off(force=True)
        self.advance_time_and_run()

        show = self.machine.shows['lights_basic'].play(
            show_tokens=dict(lights='light_01 light_02'))
        self.advance_time_and_run(.5)

        self.assertLightChannel("light_01", 255)
        self.assertLightChannel("light_02", 255)
        show.stop()

        # test led and light tags in the same show
        self.machine.lights["led_01"].clear_stack()
        self.machine.lights["led_02"].clear_stack()
        self.machine.lights["light_01"].off(force=True)
        self.machine.lights["light_02"].off(force=True)
        self.advance_time_and_run()

        show = self.machine.shows['multiple_tokens'].play(
            show_tokens=dict(leds='led_01', lights='light_01'))
        self.advance_time_and_run(.5)
        self.assertLightColor("led_01", 'blue')
        self.assertLightChannel("light_01", 255)
        show.stop()
        self.advance_time_and_run(.5)

        self.assertLightColor("led_01", 'black')
        self.assertLightColor("led_02", 'black')

        self.post_event("play_show_assoc_tokens")
        self.advance_time_and_run(.5)

        self.assertLightColor("led_01", 'red')
        self.assertLightColor("led_02", 'red')

        self.post_event("stop_show_assoc_tokens")
        self.advance_time_and_run(.5)

        self.assertLightColor("led_01", 'black')
        self.assertLightColor("led_02", 'black')

        self.post_event("test_mode_started")
        self.advance_time_and_run(.5)

        self.assertLightColor("led_01", 'red')
        self.post_event("test_mode_stopped")

    def test_get_show_copy(self):
        copied_show = self.machine.shows['test_show1'].get_show_steps()
        self.assertEqual(5, len(copied_show))
        self.assertIs(type(copied_show), list)
        self.assertEqual(copied_show[0]['duration'], 1.0)
        self.assertEqual(copied_show[1]['duration'], 1.0)
        self.assertEqual(copied_show[2]['duration'], 1.0)
        self.assertEqual(copied_show[4]['duration'], 2.0)
        self.assertIn(self.machine.lights["led_01"], copied_show[0]['lights'])
        self.assertIn(self.machine.lights["led_02"], copied_show[0]['lights'])
        self.assertEqual(copied_show[0]['lights'][self.machine.lights["led_01"]],
                         dict(color='006400', fade=None, priority=0))
        self.assertEqual(copied_show[0]['lights'][self.machine.lights["led_02"]],
                         dict(color='cccccc', fade=None, priority=0))
        self.assertEqual(copied_show[3]['lights'][self.machine.lights["led_01"]],
                         dict(color='midnightblue', fade=500, priority=0))

    def test_show_player(self):
        # Basic show
        self.machine.events.post('play_test_show1')
        self.advance_time_and_run()
        self.assertEqual(1, len(self.machine.show_player.instances['_global']['show_player']))
        self.post_event("stop_test_show1")

        # Test priority
        self.machine.events.post('play_with_priority')
        self.advance_time_and_run()
        self.assertEqual(15, self.machine.show_player.instances['_global']['show_player']['test_show1'].show_config.priority)
        self.post_event("stop_test_show1")

        # Test speed
        self.machine.events.post('play_with_speed')
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.show_player.instances['_global']['show_player']['test_show1'].show_config.speed)
        self.post_event("stop_test_show1")

        # Test start step
        self.machine.events.post('play_with_start_step')
        self.advance_time_and_run(.1)
        self.assertEqual(2, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.post_event("stop_test_show1")

        # Test start step
        self.machine.events.post('play_with_neg_start_step')
        self.advance_time_and_run(.1)
        self.assertEqual(4, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.post_event("stop_test_show1")

        # Test loops
        self.machine.events.post('play_with_loops')
        self.advance_time_and_run(.1)
        self.assertEqual(2, self.machine.show_player.instances['_global']['show_player']['test_show1'].loops)
        self.post_event("stop_test_show1")

        # Test sync_ms 1000ms
        self.machine.events.post('play_with_sync_ms_1000')
        self.advance_time_and_run(.1)

        # should be 0 +/- the duration of a frame

        self.assertAlmostEqual(0.0, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_time % 1.0, delta=(1 / 30))
        self.post_event("stop_test_show1")

        # Test sync_ms 500ms
        self.machine.events.post('play_with_sync_ms_500')
        self.advance_time_and_run(.1)
        self.assertAlmostEqual(0.0, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_time % 0.5, delta=(1 / 30))
        self.post_event("stop_test_show1")

        # Test manual advance
        self.machine.events.post('play_with_manual_advance')
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)

    def advance_to_sync_ms(self, ms):
        current_time = self.clock.get_time()
        ms = float(ms)
        next_full_second = current_time + ((ms - (current_time * 1000) % ms) / 1000.0)
        self.advance_time_and_run(next_full_second - current_time)
        delta = (self.clock.get_time() * 1000) % ms
        self.assertTrue(delta == ms or delta < 1, "Delta {} too large".format(delta))

    @test_config("test_sync_ms.yaml")
    def test_sync_ms(self):
        self.advance_to_sync_ms(250)
        # shortly after sync point. start initial show
        self.advance_time_and_run(.01)
        self.post_event("play_show_sync_ms1")
        self.assertLightColor("light", "off")
        # wait for first sync point
        self.advance_to_sync_ms(250)
        self.advance_time_and_run(.01)
        self.assertLightColor("light", "red")
        # shortly after sync point again
        self.post_event("play_show_sync_ms2")
        # old show still playing
        self.advance_time_and_run(.1)
        self.assertLightColor("light", "red")
        # until next sync point is reached
        self.advance_time_and_run(.15)
        self.assertLightColor("light", "blue")
        self.post_event("stop_show")
        self.assertLightColor("light", "off")

        # play show and start second show before first was synced
        self.advance_to_sync_ms(250)
        self.advance_time_and_run(.01)
        self.post_event("play_show_sync_ms1")
        self.advance_time_and_run(.01)
        self.post_event("play_show_sync_ms2")
        self.assertLightColor("light", "off")
        self.advance_to_sync_ms(250)
        self.assertLightColor("light", "blue")
        self.post_event("stop_show")
        self.assertLightColor("light", "off")

        # play show and start second show before first was synced. stop before second is synced
        self.advance_to_sync_ms(250)
        self.advance_time_and_run(.01)
        self.post_event("play_show_sync_ms1")
        self.advance_time_and_run(.01)
        self.post_event("play_show_sync_ms2")
        self.assertLightColor("light", "off")
        self.post_event("stop_show")
        self.assertLightColor("light", "off")
        self.advance_time_and_run(.5)
        self.assertLightColor("light", "off")

    def test_pause_resume_shows(self):
        self.machine.events.post('play_test_show1')
        # make sure show is advancing
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)

        self.machine.events.post('pause_test_show1')

        # make sure show stops advancing
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(3, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)

        # make sure show starts advanving again
        self.machine.events.post('resume_test_show1')
        self.advance_time_and_run(0.1)
        self.assertEqual(4, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.advance_time_and_run(1)
        self.assertEqual(5, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)
        self.advance_time_and_run(2)
        self.assertEqual(1, self.machine.show_player.instances['_global']['show_player']['test_show1'].next_step_index)

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
        self.assertLightColor("led_01", [255, 255, 255])
        self.assertLightColor("led_02", [0, 0, 0])

        self.post_event("play_on_led2")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [255, 255, 255])
        self.assertLightColor("led_02", [255, 255, 255])

        self.post_event("stop_on_led1")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightColor("led_02", [255, 255, 255])

        self.post_event("stop_on_led2")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 0, 0])
        self.assertLightColor("led_02", [0, 0, 0])

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
        self.assertLightColor("led_01", [0, 0, 0])
        self.post_event("play_manual_advance")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [255, 0, 0])

        self.post_event("advance_manual_advance")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 255, 0])

        self.post_event("advance_manual_advance")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 0, 255])

        self.post_event("advance_manual_step_back")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 255, 0])

        self.post_event("advance_manual_advance")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 0, 255])

        self.post_event("play_manual_advance")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [255, 0, 0])

        # test wrap around
        self.post_event("advance_manual_step_back")
        self.advance_time_and_run()
        self.assertLightColor("led_01", [0, 0, 255])

    def test_queue_event(self):
        done = MagicMock()
        self.mock_event("step1")
        self.mock_event("step2")
        self.mock_event("step3")
        self.machine.events.post_queue("queue_play", done)
        self.advance_time_and_run(.1)
        self.assertEventCalled("step1")
        self.assertEventNotCalled("step2")
        self.assertEventNotCalled("step3")
        done.assert_not_called()
        self.advance_time_and_run(1)
        self.assertEventCalled("step1")
        self.assertEventCalled("step2")
        self.assertEventNotCalled("step3")
        done.assert_not_called()
        self.advance_time_and_run(1)
        self.assertEventCalled("step1")
        self.assertEventCalled("step2")
        self.assertEventCalled("step3")
        done.assert_not_called()
        self.mock_event("step1")
        self.mock_event("step2")
        self.mock_event("step3")
        self.advance_time_and_run(1)
        self.assertEventNotCalled("step1")
        self.assertEventNotCalled("step2")
        self.assertEventNotCalled("step3")
        done.assert_called_once_with()

    def test_show_player_emitted_events(self):
        self.mock_event('test_show1_played')
        self.mock_event('test_show1_played2')
        self.mock_event('test_show1_stopped')
        self.mock_event('test_show1_looped')
        self.mock_event('test_show1_paused')
        self.mock_event('test_show1_resumed')
        self.mock_event('test_show1_advanced')
        self.mock_event('test_show1_stepped_back')
        self.mock_event('test_show1_completed')

        self.machine.events.post('play_with_emitted_events')
        self.advance_time_and_run(1)
        self.assertEventCalled('test_show1_played')
        self.assertEventCalled('test_show1_played2')
        self.assertEventNotCalled('test_show1_stopped')
        self.assertEventNotCalled('test_show1_looped')
        self.assertEventNotCalled('test_show1_paused')
        self.assertEventNotCalled('test_show1_resumed')
        self.assertEventNotCalled('test_show1_advanced')
        self.assertEventNotCalled('test_show1_stepped_back')
        self.assertEventNotCalled('test_show1_completed')

        self.advance_time_and_run(6)
        self.assertEventCalled('test_show1_looped')
        self.assertEventNotCalled('test_show1_stopped')
        self.assertEventNotCalled('test_show1_paused')
        self.assertEventNotCalled('test_show1_resumed')
        self.assertEventNotCalled('test_show1_advanced')
        self.assertEventNotCalled('test_show1_stepped_back')

        self.machine.events.post('pause_emitted_events_show')
        self.advance_time_and_run(1)
        self.assertEventCalled('test_show1_paused')

        self.machine.events.post('advance_emitted_events_show')
        self.advance_time_and_run(1)
        self.assertEventCalled('test_show1_advanced')

        self.machine.events.post('step_back_emitted_events_show')
        self.advance_time_and_run(1)
        self.assertEventCalled('test_show1_stepped_back')

        self.machine.events.post('resume_emitted_events_show')
        self.advance_time_and_run(1)
        self.assertEventCalled('test_show1_resumed')

        self.machine.events.post('stop_emitted_events_show')
        self.advance_time_and_run(1)
        self.assertEventCalled('test_show1_stopped')

        self.assertEventNotCalled('test_show1_completed')

    def test_show_player_completed_events(self):
        self.mock_event('test_show1_completed')
        self.mock_event('test_show1_stopped')

        self.machine.events.post('play_with_completed_event')
        self.advance_time_and_run(1)
        self.assertEventNotCalled('test_show1_completed')
        self.assertEventNotCalled('test_show1_stopped')

        self.advance_time_and_run(6)
        self.assertEventCalled('test_show1_completed')
        self.assertEventCalled('test_show1_stopped')

    def test_token_in_keys(self):
        self.post_event("play_show_with_token_in_key")
        self.advance_time_and_run()
        self.assertLightColor("led_01", "red")

    def test_non_string_token(self):
        self.start_mode("mode4")
        self.assertLightColor("led_01", "black")
        self.post_event("test_token")
        self.advance_time_and_run(.05)
        self.assertNotLightColor("led_01", "red")
        self.advance_time_and_run(.06)
        self.assertLightColor("led_01", "red")
