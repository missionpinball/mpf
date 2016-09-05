"""Test the LED device."""
from mpf.devices.led import Led

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestLed(MpfTestCase):

    def getConfigFile(self):
        return 'led.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/led/'

    def _synchronise_led_update(self):
        ts = Led._updater_task.get_next_call_time()
        self.assertTrue(ts)
        self.advance_time_and_run(ts - self.machine.clock.get_time())
        self.advance_time_and_run(.01)

    def test_color_and_stack(self):
        led1 = self.machine.leds.led1

        self._synchronise_led_update()

        # set led1 to red and check the color and stack
        led1.color('red')

        # need to advance time since LEDs are updated once per frame via a
        # clock.schedule_interval
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        color_setting = led1.stack[0]
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'], 0)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor('red'))
        self.assertIsNone(color_setting['key'])

        # test get_color()
        self.assertEqual(led1.get_color(), RGBColor('red'))

        # set to blue & test
        led1.color('blue')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        color_setting = led1.stack[0]
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('red'))
        self.assertEqual(color_setting['dest_time'], 0)
        self.assertEqual(color_setting['dest_color'], RGBColor('blue'))
        self.assertEqual(color_setting['color'], RGBColor('blue'))
        self.assertIsNone(color_setting['key'])
        self.assertEqual(len(led1.stack), 1)

        # set it to green, at a higher priority, but with no key. Stack should
        # reflect the higher priority, but still be len 1 since the key is the
        # same (None)
        led1.color('green', priority=100)

        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(len(led1.stack), 1)
        color_setting = led1.stack[0]
        self.assertEqual(color_setting['priority'], 100)
        self.assertEqual(color_setting['start_color'], RGBColor('blue'))
        self.assertEqual(color_setting['dest_time'], 0)
        self.assertEqual(color_setting['dest_color'], RGBColor('green'))
        self.assertEqual(color_setting['color'], RGBColor('green'))
        self.assertIsNone(color_setting['key'])

        # set led1 orange, lower priority, but with a key, so led should stay
        # green, but stack len should be 2
        led1.color('orange', key='test')

        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('green').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(len(led1.stack), 2)
        color_setting = led1.stack[0]
        self.assertEqual(color_setting['priority'], 100)
        self.assertEqual(color_setting['start_color'], RGBColor('blue'))
        self.assertEqual(color_setting['dest_time'], 0)
        self.assertEqual(color_setting['dest_color'], RGBColor('green'))
        self.assertEqual(color_setting['color'], RGBColor('green'))
        self.assertIsNone(color_setting['key'])

        # remove the orange key from the stack
        led1.remove_from_stack_by_key('test')
        self.assertEqual(len(led1.stack), 1)

        # clear the stack
        led1.clear_stack()
        self.assertEqual(len(led1.stack), 0)

        # test the stack ordering with different priorities & keys
        led1.color('red', priority=200, key='red')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        led1.color('blue', priority=300, key='blue')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        led1.color('green', priority=200, key='green')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        led1.color('orange', priority=100, key='orange')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        # verify the stack is right
        # order should be priority, then insertion order (recent is higher), so
        # should be: blue, green, red, orange
        self.assertEqual(RGBColor('blue'), led1.stack[0]['color'])
        self.assertEqual(RGBColor('green'), led1.stack[1]['color'])
        self.assertEqual(RGBColor('red'), led1.stack[2]['color'])
        self.assertEqual(RGBColor('orange'), led1.stack[3]['color'])

        # test that a replacement key slots in properly
        led1.color('red', priority=300, key='red')
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(RGBColor('red'), led1.stack[0]['color'])
        self.assertEqual(RGBColor('blue'), led1.stack[1]['color'])
        self.assertEqual(RGBColor('green'), led1.stack[2]['color'])
        self.assertEqual(RGBColor('orange'), led1.stack[3]['color'])

    def test_fades(self):
        led1 = self.machine.leds.led1

        self._synchronise_led_update()
        led1.color('red', fade_ms=2000)
        self.advance_time_and_run(0.02)

        # check the stack before the fade starts
        color_setting = led1.stack[0]
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'],
                         color_setting['start_time'] + 2)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor('off'))
        self.assertIsNone(color_setting['key'])

        # advance to half way through the fade
        self.advance_time_and_run(1)

        self.assertTrue(led1.fade_in_progress)
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'],
                         color_setting['start_time'] + 2)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor((128, 0, 0)))
        self.assertIsNone(color_setting['key'])
        self.assertEqual([128, 0, 0], self.machine.leds.led1.hw_driver.current_color)

        # advance to after the fade is done
        self.advance_time_and_run(2)

        self.assertFalse(led1.fade_in_progress)
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'], 0)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor('red'))
        self.assertIsNone(color_setting['key'])
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        led = self.machine.leds.led4
        self.assertEqual(1000, led.default_fade_ms)
        self._synchronise_led_update()
        led.color('white')
        self.advance_time_and_run(.02)
        self.advance_time_and_run(.5)
        self.assertEqual([130, 130, 130], led.hw_driver.current_color)
        self.advance_time_and_run(.5)
        self.assertEqual([255, 255, 255], led.hw_driver.current_color)

    def test_interrupted_fade(self):
        led1 = self.machine.leds.led1

        self._synchronise_led_update()
        led1.color('red', fade_ms=2000)
        self.advance_time_and_run(0.02)

        # check the stack before the fade starts
        color_setting = led1.stack[0]
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'],
                         color_setting['start_time'] + 2)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor('off'))
        self.assertIsNone(color_setting['key'])

        # advance to half way through the fade
        self.advance_time_and_run(1)

        self.assertTrue(led1.fade_in_progress)
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'],
                         color_setting['start_time'] + 2)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor((128, 0, 0)))
        self.assertIsNone(color_setting['key'])
        self.assertEqual([128, 0, 0], self.machine.leds.led1.hw_driver.current_color)

        # kill the fade
        led1._end_fade()

        # advance to after the fade should have been done
        self.advance_time_and_run(2)

        # everything should still be the same as the last check (except
        # dest_time should be 0)
        self.assertFalse(led1.fade_in_progress)
        self.assertEqual(color_setting['priority'], 0)
        self.assertEqual(color_setting['start_color'], RGBColor('off'))
        self.assertEqual(color_setting['dest_time'], 0)
        self.assertEqual(color_setting['dest_color'], RGBColor('red'))
        self.assertEqual(color_setting['color'], RGBColor((128, 0, 0)))
        self.assertIsNone(color_setting['key'])
        self.assertEqual([128, 0, 0], self.machine.leds.led1.hw_driver.current_color)

    def test_restore_to_fade_in_progress(self):
        led1 = self.machine.leds.led1

        self._synchronise_led_update()
        led1.color('red', fade_ms=4000)
        self.advance_time_and_run(0.02)
        self.advance_time_and_run(1)

        # fade is 25% complete
        self.assertEqual([64, 0, 0], self.machine.leds.led1.hw_driver.current_color)

        # higher priority color which goes on top of fade (higher priority
        # becuase it was added after the first, even though the priorities are
        # the same)
        led1.color('blue', key='test')
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertFalse(led1.fade_in_progress)

        led1.remove_from_stack_by_key('test')
        # should go back to the fade in progress, which is now 75% complete
        self.advance_time_and_run(1)
        self.assertEqual([191, 0, 0], self.machine.leds.led1.hw_driver.current_color)
        self.assertTrue(led1.fade_in_progress)

        # go to 1 sec after fade and make sure it finished
        self.advance_time_and_run(2)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertFalse(led1.fade_in_progress)

    def test_multiple_concurrent_fades(self):
        # start one fade, and while that's in progress, start a second fade.
        # the second fade should start from the wherever the current fade was.

        led1 = self.machine.leds.led1

        self._synchronise_led_update()
        led1.color('red', fade_ms=4000)
        self.advance_time_and_run(0.02)
        self.advance_time_and_run(1)

        # fade is 25% complete
        self.assertEqual([64, 0, 0],
                         self.machine.leds.led1.hw_driver.current_color)

        # start a blue 2s fade
        led1.color('blue', key='test', fade_ms=2000)

        # advance 1s, since we're half way to the blue fade from the 25% red,
        # we should now be at 12.5% red and 50% blue
        # Note: technically the red fade should continue even as it's being
        # faded to blue, but meh, we'll handle that with alpha channels in the
        # future
        self.advance_time_and_run(1)
        self.assertEqual([33, 0, 126], self.machine.leds.led1.hw_driver.current_color)

        # advance past the end
        self.advance_time_and_run(2)
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertFalse(led1.fade_in_progress)

    def test_color_correction(self):
        led = self.machine.leds.led_corrected
        led.color(RGBColor("white"))
        self.advance_time_and_run()
        self.assertEqual([210, 184, 159], led.hw_driver.current_color)

        led.color(RGBColor([128, 128, 128]))
        self.advance_time_and_run()
        self.assertEqual([96, 83, 70], led.hw_driver.current_color)

        led.color(RGBColor("black"))
        self.advance_time_and_run()
        self.assertEqual([0, 0, 0], led.hw_driver.current_color)

    def test_non_rgb_leds(self):
        # test bgr
        led = self.machine.leds.led2

        led.color(RGBColor((11, 23, 42)))
        self.advance_time_and_run(1)

        self.assertEqual([42, 23, 11], led.hw_driver.current_color)

        # test rgbw
        led = self.machine.leds.led3

        led.color(RGBColor((11, 23, 42)))
        self.advance_time_and_run(1)

        self.assertEqual([11, 23, 42, 11], led.hw_driver.current_color)

        # test w+-
        led = self.machine.leds.led5

        led.color(RGBColor((100, 100, 100)))
        self.advance_time_and_run(1)

        self.assertEqual([100, 255, 0], led.hw_driver.current_color)

    def test_leds_on_matrix_lights(self):
        led = self.machine.leds.led_lights

        led.color(RGBColor((11, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual(11, self.machine.lights.light_r.hw_driver.current_brightness)
        self.assertEqual(23, self.machine.lights.light_g.hw_driver.current_brightness)
        self.assertEqual(42, self.machine.lights.light_b.hw_driver.current_brightness)

        self.machine.create_machine_var("brightness", 0.8)
        led.color(RGBColor((100, 200, 10)))
        self.advance_time_and_run(1)
        self.assertEqual(80, self.machine.lights.light_r.hw_driver.current_brightness)
        self.assertEqual(160, self.machine.lights.light_g.hw_driver.current_brightness)
        self.assertEqual(8, self.machine.lights.light_b.hw_driver.current_brightness)

    def test_brightness_correction(self):
        led = self.machine.leds.led1

        led.color(RGBColor((100, 100, 100)))
        self.advance_time_and_run(1)
        self.assertEqual([100, 100, 100], self.machine.leds.led1.hw_driver.current_color)

        self.machine.create_machine_var("brightness", 0.8)
        led.color(RGBColor((100, 100, 100)))
        self.advance_time_and_run(1)

        self.assertEqual([80, 80, 80], self.machine.leds.led1.hw_driver.current_color)

