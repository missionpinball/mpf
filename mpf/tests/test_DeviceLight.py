"""Test the LED device."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase, test_config


class TestDeviceLight(MpfTestCase):

    def getConfigFile(self):
        return 'light.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/light/'

    def test_default_on_color(self):
        led = self.machine.lights["led1"]

        # color on should map to red
        led.color("on")
        self.assertLightColor("led1", RGBColor("red"))

        # turn off again
        led.off()
        self.assertLightColor("led1", RGBColor("black"))

        # on should also map to red
        led.on()
        self.assertLightColor("led1", RGBColor("red"))

        # on with half brightness should map to dimmed red
        led.on(127)
        self.assertLightColor("led1", RGBColor("red%50"))

    @test_config("light_default_color_correction.yaml")
    def test_default_color_correction(self):
        led = self.machine.lights["led1"]
        led.color(RGBColor("white"))
        self.advance_time_and_run()
        # color is uncorrected
        self.assertLightColor("led1", RGBColor("white"))
        # corrected color
        self.assertEqual(RGBColor([210, 184, 159]), led.color_correct(led.get_color()))
        # check hardware
        self.assertEqual(210 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(184 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(159 / 255.0, led.hw_drivers["blue"][0].current_brightness)

        led.color(RGBColor([128, 128, 128]))
        self.advance_time_and_run()
        self.assertLightColor("led1", [128, 128, 128])
        self.assertEqual(RGBColor([96, 83, 70]), led.color_correct(led.get_color()))
        self.assertEqual(96 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(83 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(70 / 255.0, led.hw_drivers["blue"][0].current_brightness)

        led.color(RGBColor("black"))
        self.advance_time_and_run()
        self.assertLightColor("led1", [0, 0, 0])
        self.assertEqual(RGBColor([0, 0, 0]), led.color_correct(led.get_color()))
        self.assertEqual(0 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(0 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(0 / 255.0, led.hw_drivers["blue"][0].current_brightness)

    def test_consecutive_fades(self):
        self.assertLightColor("led1", [0, 0, 0])
        led = self.machine.lights["led1"]
        led.color(RGBColor("red"), fade_ms=1000, key="one")
        self.advance_time_and_run(.5)
        self.assertLightColor("led1", [127, 0, 0])
        self.advance_time_and_run(1)
        self.assertLightColor("led1", "red")

        # play another color with the same key
        led.color(RGBColor("red"), fade_ms=1000, key="one")
        self.advance_time_and_run(.1)
        self.assertLightColor("led1", "red")
        self.advance_time_and_run(1)

        # remove key and play again
        led.remove_from_stack_by_key("one", fade_ms=1000)
        led.color(RGBColor("red"), fade_ms=1000, key="one")
        self.advance_time_and_run(.1)
        self.assertLightColor("led1", "red")
        self.advance_time_and_run(1)

        led.remove_from_stack_by_key("one", fade_ms=1000)
        self.assertLightColor("led1", "red")
        self.advance_time_and_run(.5)
        self.assertLightColor("led1", [128, 0, 0])
        self.advance_time_and_run(.6)
        self.assertLightColor("led1", [0, 0, 0])
        self.assertFalse(led.stack)

        led.color(RGBColor("blue"), key="lower", priority=1, fade_ms=10000)
        led.color(RGBColor("red"), key="upper", priority=2, fade_ms=1000)
        self.advance_time_and_run(.5)
        self.assertLightColor("led1", [127, 0, 0])
        self.advance_time_and_run(.51)
        self.assertLightColor("led1", "red")
        self.advance_time_and_run(2)    # lower is at 3/10
        led.remove_from_stack_by_key("upper", fade_ms=4000)
        self.assertLightColor("led1", "red")
        self.advance_time_and_run(2)    # lower is at 5/10 -> [0, 0, 127]. upper at 2/4 (50% alpha)
        self.assertLightColor("led1", [128, 0, 63])
        self.advance_time_and_run(2)    # lower is at 7/10. upper is gone
        self.assertLightColor("led1", [0, 0, 178])
        self.advance_time_and_run(3)    # lower is at 10/10. upper is gone
        self.assertLightColor("led1", [0, 0, 255])
        self.assertEqual(1, len(led.stack))

    def test_color_and_stack(self):
        led1 = self.machine.lights["led1"]

        # set led1 to red and check the color and stack
        led1.color('red')

        # need to advance time since LEDs are updated once per frame via a
        # clock.schedule_interval
        self.advance_time_and_run()
        self.assertLightColor("led1", "red")

        color_setting = led1.stack[0]
        self.assertEqual(color_setting.priority, 0)
        self.assertEqual(color_setting.start_color, RGBColor('off'))
        self.assertEqual(color_setting.dest_time, 0)
        self.assertEqual(color_setting.dest_color, RGBColor('red'))
        self.assertEqual(led1.get_color(), RGBColor('red'))
        self.assertFalse(color_setting.key)

        # test get_color()
        self.assertEqual(led1.get_color(), RGBColor('red'))

        # set to blue & test
        led1.color('blue')
        self.advance_time_and_run()
        self.assertLightColor("led1", "blue")
        color_setting = led1.stack[0]
        self.assertEqual(color_setting.priority, 0)
        # self.assertEqual(color_setting.start_color, RGBColor('red'))
        self.assertEqual(color_setting.dest_time, 0)
        self.assertEqual(color_setting.dest_color, RGBColor('blue'))
        self.assertEqual(led1.get_color(), RGBColor('blue'))
        self.assertFalse(color_setting.key)
        self.assertEqual(len(led1.stack), 1)

        # set it to green, at a higher priority, but with no key. Stack should
        # reflect the higher priority, but still be len 1 since the key is the
        # same (None)
        led1.color('green', priority=100)

        self.advance_time_and_run()
        self.assertLightColor("led1", "green")
        self.assertEqual(len(led1.stack), 1)
        color_setting = led1.stack[0]
        self.assertEqual(color_setting.priority, 100)
        # self.assertEqual(color_setting.start_color, RGBColor('blue'))
        self.assertEqual(color_setting.dest_time, 0)
        self.assertEqual(color_setting.dest_color, RGBColor('green'))
        self.assertEqual(led1.get_color(), RGBColor('green'))
        self.assertFalse(color_setting.key)

        # set led1 orange, lower priority, but with a key, so led should stay
        # green, but stack len should be 2
        led1.color('orange', key='test')

        self.advance_time_and_run()
        self.assertLightColor("led1", "green")
        self.assertEqual(len(led1.stack), 2)
        color_setting = led1.stack[0]
        self.assertEqual(color_setting.priority, 100)
        # self.assertEqual(color_setting.start_color, RGBColor('blue'))
        self.assertEqual(color_setting.dest_time, 0)
        self.assertEqual(color_setting.dest_color, RGBColor('green'))
        self.assertEqual(led1.get_color(), RGBColor('green'))
        self.assertFalse(color_setting.key)

        # remove the orange key from the stack
        led1.remove_from_stack_by_key('test')
        self.assertEqual(len(led1.stack), 1)

        # clear the stack
        led1.clear_stack()
        self.assertEqual(len(led1.stack), 0)

        # test the stack ordering with different priorities & keys
        led1.color('red', priority=200, key='red')
        self.advance_time_and_run()
        self.assertLightColor("led1", "red")

        led1.color('blue', priority=300, key='blue')
        self.advance_time_and_run()
        self.assertLightColor("led1", "blue")

        led1.color('green', priority=200, key='green')
        self.advance_time_and_run()
        self.assertLightColor("led1", "blue")

        led1.color('orange', priority=100, key='orange')
        self.advance_time_and_run()
        self.assertLightColor("led1", "blue")

        # verify the stack is right
        # order should be priority, then key, so
        # should be: blue, green, red, orange
        self.assertEqual(RGBColor('blue'), led1.stack[0].dest_color)
        self.assertEqual(RGBColor('red'), led1.stack[1].dest_color)
        self.assertEqual(RGBColor('green'), led1.stack[2].dest_color)
        self.assertEqual(RGBColor('orange'), led1.stack[3].dest_color)

        # test that a replacement key slots in properly
        led1.color('red', priority=300, key='red')
        self.advance_time_and_run()
        self.assertLightColor("led1", "red")
        self.assertEqual(RGBColor('red'), led1.stack[0].dest_color)
        self.assertEqual(RGBColor('blue'), led1.stack[1].dest_color)
        self.assertEqual(RGBColor('green'), led1.stack[2].dest_color)
        self.assertEqual(RGBColor('orange'), led1.stack[3].dest_color)

    def test_named_colors(self):
        led1 = self.machine.lights["led1"]
        led1.color('jans_red')
        self.machine_run()

        self.assertLightColor(led1.name, "jans_red")
        self.assertLightColor(led1.name, [251, 23, 42])

    def test_fades(self):
        led1 = self.machine.lights["led1"]

        led1.color('red', fade_ms=2000)
        self.machine_run()

        # check the stack before the fade starts
        color_setting = led1.stack[0]
        self.assertEqual(color_setting.priority, 0)
        self.assertEqual(color_setting.start_color, RGBColor('off'))
        self.assertEqual(color_setting.dest_time,
                         color_setting.start_time + 2)
        self.assertEqual(color_setting.dest_color, RGBColor('red'))
        self.assertEqual(led1.get_color(), RGBColor('off'))
        self.assertFalse(color_setting.key)

        # advance to half way through the fade
        self.advance_time_and_run(1)

        self.assertTrue(led1.fade_in_progress)
        self.assertEqual(color_setting.priority, 0)
        self.assertEqual(color_setting.start_color, RGBColor('off'))
        self.assertEqual(color_setting.dest_time,
                         color_setting.start_time + 2)
        self.assertEqual(color_setting.dest_color, RGBColor('red'))
        self.assertEqual(led1.get_color(), RGBColor((127, 0, 0)))
        self.assertFalse(color_setting.key)
        self.assertLightColor("led1", [127, 0, 0])

        # advance to after the fade is done
        self.advance_time_and_run(2)

        self.assertFalse(led1.fade_in_progress)
        self.assertEqual(color_setting.priority, 0)
        self.assertEqual(color_setting.start_color, RGBColor('off'))
        self.assertEqual(color_setting.dest_color, RGBColor('red'))
        self.assertEqual(led1.get_color(), RGBColor('red'))
        self.assertFalse(color_setting.key)
        self.assertLightColor("led1", "red")

        led = self.machine.lights["led4"]
        self.assertEqual(1000, led.default_fade_ms)
        led.color('white')
        self.advance_time_and_run(.02)
        self.advance_time_and_run(.5)
        self.assertLightColor("led4", [132, 132, 132])
        self.advance_time_and_run(.5)
        self.assertLightColor("led4", [255, 255, 255])

    def test_restore_to_fade_in_progress(self):
        led1 = self.machine.lights["led1"]

        led1.color('red', fade_ms=4000, priority=50)
        self.advance_time_and_run(0.02)
        self.advance_time_and_run(1)

        # fade is 25% complete
        self.assertLightColor("led1", [65, 0, 0])

        # higher priority color which goes on top of fade
        led1.color('blue', key='test', priority=100)
        self.advance_time_and_run(1)
        self.assertLightColor("led1", 'blue')
        self.assertFalse(led1.fade_in_progress)

        led1.remove_from_stack_by_key('test')
        # should go back to the fade in progress, which is now 75% complete
        self.advance_time_and_run(1)
        self.assertLightColor("led1", [192, 0, 0])
        self.assertTrue(led1.fade_in_progress)

        # go to 1 sec after fade and make sure it finished
        self.advance_time_and_run(2)
        self.assertLightColor("led1", 'red')
        self.assertFalse(led1.fade_in_progress)

    def test_multiple_concurrent_fades(self):
        # start one fade, and while that's in progress, start a second fade.
        # the second fade should start from the wherever the current fade was.

        led1 = self.machine.lights["led1"]

        led1.color('red', fade_ms=4000, priority=50)
        self.advance_time_and_run(0.02)
        self.advance_time_and_run(1)

        # fade is 25% complete
        self.assertLightColor("led1", [65, 0, 0])

        # start a blue 2s fade
        led1.color('blue', key='test', fade_ms=2000, priority=100)

        # advance 1s, since we're half way to the blue fade from the 25% red,
        # we should now be at 12.5% red and 50% blue
        # Note: technically the red fade should continue even as it's being
        # faded to blue, but meh, we'll handle that with alpha channels in the
        # future
        self.advance_time_and_run(1)

        self.assertLightColor("led1", [33, 0, 127])

        # advance past the end
        self.advance_time_and_run(2)
        self.assertLightColor("led1", 'blue')
        self.assertFalse(led1.fade_in_progress)

    def test_color_correction(self):
        led = self.machine.lights["led_corrected"]
        led.color(RGBColor("white"))
        self.advance_time_and_run()
        # color is uncorrected
        self.assertLightColor("led_corrected", RGBColor("white"))
        # corrected color
        self.assertEqual(RGBColor([210, 184, 159]), led.color_correct(led.get_color()))
        # check hardware
        self.assertEqual(210 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(184 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(159 / 255.0, led.hw_drivers["blue"][0].current_brightness)

        led.color(RGBColor([128, 128, 128]))
        self.advance_time_and_run()
        self.assertLightColor("led_corrected", [128, 128, 128])
        self.assertEqual(RGBColor([96, 83, 70]), led.color_correct(led.get_color()))
        self.assertEqual(96 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(83 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(70 / 255.0, led.hw_drivers["blue"][0].current_brightness)

        led.color(RGBColor("black"))
        self.advance_time_and_run()
        self.assertLightColor("led_corrected", [0, 0, 0])
        self.assertEqual(RGBColor([0, 0, 0]), led.color_correct(led.get_color()))
        self.assertEqual(0 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(0 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(0 / 255.0, led.hw_drivers["blue"][0].current_brightness)

    def test_non_rgb_leds(self):
        # test bgr
        led = self.machine.lights["led2"]

        led.color(RGBColor((11, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual(42 / 255, led.hw_drivers["blue"][0].current_brightness)
        self.assertEqual('led-2', led.hw_drivers["blue"][0].number)
        self.assertEqual(23 / 255, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual('led-3', led.hw_drivers["green"][0].number)
        self.assertEqual(11 / 255, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual('led-4', led.hw_drivers["red"][0].number)

        led = self.machine.lights["led_bgr_2"]
        led.color(RGBColor((11, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual(42 / 255, led.hw_drivers["blue"][0].current_brightness)
        self.assertEqual('led-42-r', led.hw_drivers["blue"][0].number)
        self.assertEqual(23 / 255, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual('led-42-g', led.hw_drivers["green"][0].number)
        self.assertEqual(11 / 255, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual('led-42-b', led.hw_drivers["red"][0].number)

        # test rgbw
        led = self.machine.lights["led3"]

        led.color(RGBColor((11, 23, 42)))
        self.advance_time_and_run(1)
        self.assertLightColor("led2", [11, 23, 42])
        self.assertEqual(11 / 255, led.hw_drivers["white"][0].current_brightness)
        self.assertEqual('led-10', led.hw_drivers["white"][0].number)

        # test www light
        led = self.machine.lights["led_www"]
        led.on(128)
        self.advance_time_and_run(1)
        self.assertLightColor("led_www", [128, 128, 128])
        self.assertEqual(128 / 255, led.hw_drivers["white"][0].current_brightness)
        self.assertEqual('led-23-r', led.hw_drivers["white"][0].number)
        self.assertEqual(128 / 255, led.hw_drivers["white"][1].current_brightness)
        self.assertEqual('led-23-g', led.hw_drivers["white"][1].number)
        self.assertEqual(128 / 255, led.hw_drivers["white"][2].current_brightness)
        self.assertEqual('led-23-b', led.hw_drivers["white"][2].number)

    def test_brightness_correction(self):
        led = self.machine.lights["led1"]

        led.color(RGBColor((100, 100, 100)))
        self.advance_time_and_run(1)
        self.assertLightColor("led1", [100, 100, 100])
        self.assertEqual(100 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(100 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(100 / 255.0, led.hw_drivers["blue"][0].current_brightness)

        self.machine.set_machine_var("brightness", 0.8)
        led.color(RGBColor((100, 100, 100)))
        self.advance_time_and_run(1)

        self.assertLightColor("led1", [100, 100, 100])
        self.assertEqual(80 / 255.0, led.hw_drivers["red"][0].current_brightness)
        self.assertEqual(80 / 255.0, led.hw_drivers["green"][0].current_brightness)
        self.assertEqual(80 / 255.0, led.hw_drivers["blue"][0].current_brightness)


class TestLightOnDriver(MpfTestCase):

    def getConfigFile(self):
        return 'lights_on_drivers.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/light/'

    def get_platform(self):
        # no force platform. we are testing the drivers platform
        return False

    def test_driver_platform(self):
        driver = self.machine.coils["coil_01"].hw_driver
        self.assertEqual("disabled", driver.state)
        self.machine.lights["light_on_driver"].on()
        self.assertEqual("enabled", driver.state)
        self.machine.lights["light_on_driver"].off()
        self.assertEqual("disabled", driver.state)
