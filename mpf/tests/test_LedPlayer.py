"""Test led player."""
from mpf.devices.led import Led

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase

from mpf.core.config_player import ConfigPlayer


class TestLedPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'led_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/led_player/'

    def _synchronise_led_update(self):
        ts = Led._updater_task.get_next_call_time()
        self.assertTrue(ts)
        self.advance_time_and_run(ts - self.machine.clock.get_time())
        self.advance_time_and_run(.01)

    def test_config_player_config_processing(self):
        led1 = self.machine.leds.led1
        led2 = self.machine.leds.led2
        led3 = self.machine.leds.led3

        self.assertEqual(self.machine.config['led_player']['event1'][led1]['color'], 'red')
        self.assertEqual(self.machine.config['led_player']['event1'][led1]['fade_ms'], 0)
        self.assertEqual(self.machine.config['led_player']['event1'][led1]['priority'], 200)
        self.assertEqual(self.machine.config['led_player']['event1'][led2]['color'], 'ff0000')
        self.assertEqual(self.machine.config['led_player']['event1'][led2]['fade_ms'], 0)
        self.assertEqual(self.machine.config['led_player']['event1'][led3]['color'], 'red')
        self.assertEqual(self.machine.config['led_player']['event1'][led3]['fade_ms'], 0)

        self.assertEqual(self.machine.config['led_player']['event2'][led1]['color'], 'blue')
        self.assertEqual(self.machine.config['led_player']['event2'][led1]['fade_ms'], 200)
        self.assertEqual(self.machine.config['led_player']['event2'][led1]['priority'], 100)
        self.assertEqual(self.machine.config['led_player']['event2'][led2]['color'], 'blue')
        self.assertEqual(self.machine.config['led_player']['event2'][led2]['fade_ms'], 200)
        self.assertEqual(self.machine.config['led_player']['event2'][led1]['priority'], 100)

        self.assertEqual(self.machine.config['led_player']['event3'][led1]['color'], 'lime')
        self.assertEqual(self.machine.config['led_player']['event3'][led1]['fade_ms'], 500)
        self.assertEqual(self.machine.config['led_player']['event3'][led2]['color'], 'lime')
        self.assertEqual(self.machine.config['led_player']['event3'][led2]['fade_ms'], 500)
        self.assertEqual(self.machine.config['led_player']['event3'][led3]['color'], '00ff00')
        self.assertEqual(self.machine.config['led_player']['event3'][led3]['fade_ms'], 500)

        self.assertEqual(self.machine.config['led_player']['event4'][led1]['color'], '00ffff')
        self.assertEqual(self.machine.config['led_player']['event4'][led1]['fade_ms'], 0)
        self.assertEqual(self.machine.config['led_player']['event4'][led2]['color'], '00ffff')
        self.assertEqual(self.machine.config['led_player']['event4'][led2]['fade_ms'], 0)

    def test_led_player(self):
        # led_player just sets these colors and that's it.
        self.machine.events.post('event1')
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.stack[0]['priority'])

        self.assertEqual(list(RGBColor('ff0000').rgb),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led2.stack[0]['priority'])

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led3.stack[0]['priority'])

        # should stay in this state forever
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.stack[0]['priority'])

        # test tags and fade in expanded config

        # post event2, which is a tag with led1 and led2, but at priority 100
        # led1 should remain unchanged since it was set at priority 200,
        # led2 should fade to blue since it was red before at priority 0
        self._synchronise_led_update()
        self.machine.events.post('event2')
        self.advance_time_and_run(.1)

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.stack[0]['priority'])

        # fade is half way from red to blue
        self.assertEqual([141, 0, 114], self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(100, self.machine.leds.led2.stack[0]['priority'])

        self.advance_time_and_run()

        # fade is done
        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led2.hw_driver.current_color)

        # reset leds
        self.machine.leds.led1.clear_stack()
        self.machine.leds.led2.clear_stack()
        self.machine.leds.led3.clear_stack()
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led1.stack[0]['priority'])

        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led2.stack[0]['priority'])

        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led3.stack[0]['priority'])

        # test fades via express config with a few different options
        self._synchronise_led_update()
        self.machine.events.post('event3')

        # fades are 500ms, so advance 250 and check
        self.advance_time_and_run(.26)
        self.assertEqual([0, 127, 0],
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual([0, 127, 0],
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual([0, 127, 0],
                         self.machine.leds.led3.hw_driver.current_color)

        # finish the fade
        self.advance_time_and_run()
        self.assertEqual([0, 255, 0],
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual([0, 255, 0],
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual([0, 255, 0],
                         self.machine.leds.led3.hw_driver.current_color)

        # reset leds
        self.machine.leds.led1.clear_stack()
        self.machine.leds.led2.clear_stack()
        self.machine.leds.led3.clear_stack()
        self.advance_time_and_run()

        # tag1 is led1 and led2
        self.machine.events.post('event4')
        self.advance_time_and_run()

        self.assertEqual([0, 255, 255],
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual([0, 255, 255],
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led3.hw_driver.current_color)

        # test led5 with default color red
        self.assertEqual(list(RGBColor('off').rgb),
                         self.machine.leds.led5.hw_driver.current_color)

        self.post_event("event5")
        self.advance_time_and_run()
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led5.hw_driver.current_color)

    def test_single_step_show(self):
        # with single step shows, loops are automatically set to 0, hold is
        # automatically set to true

        self.machine.shows['show1'].play()
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        # when a show ends with hold, the final step of the show will cache
        # the led settings
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.stack[0]['color'])
        self.assertEqual(0, self.machine.leds.led1.stack[0]['priority'])

    def test_show_hold_leds(self):
        self.machine.shows['show2_stay_on'].play(loops=0)
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.stack[0]['color'])
        self.assertEqual(0, self.machine.leds.led1.stack[0]['priority'])

    def test_show_no_hold_leds(self):
        show = self.machine.shows['show2'].play(loops=0)
        self.advance_time_and_run(.1)

        # led should be red while show is running
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        self.advance_time_and_run()

        # led should be off when show ends
        self.assertEqual(RGBColor('off'),
                         self.machine.leds.led1.stack[0]['color'])
        self.assertEqual(0, self.machine.leds.led1.stack[0]['priority'])

    def test_show_same_priority(self):
        # start show2, leds are red
        self.machine.shows['show2'].play()
        self.advance_time_and_run(.5)

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        # start show3 at same priority, leds should be blue
        self.machine.shows['show3'].play()
        # timing is 600ms after show2 start, since show2 will set them to red
        # again
        self.advance_time_and_run(.1)

        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

    def test_show_higher_priority(self):
        # start show2, leds are red

        self.machine.shows['show2'].play()
        self.advance_time_and_run(.5)

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        # start show3 at same priority, leds should be blue
        show3 = self.machine.shows['show3'].play(priority=100)
        # timing is 600ms after show2 start, since show2 will set them to red
        # again
        self.advance_time_and_run(.1)

        self.assertEqual(list(RGBColor('blue').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        # stop show3, leds should go back to red
        show3.stop()
        self.advance_time_and_run(.1)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

        # and they should stay red
        self.advance_time_and_run(.5)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)

    def test_led_player_in_mode(self):
        # post event1 to get the leds set in the base config
        self.machine.events.post('event1')
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led3.hw_driver.current_color)

        # post event5, nothing should change
        self.machine.events.post('event5')
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.stack[0]['priority'])
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led2.stack[0]['priority'])
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led3.stack[0]['priority'])

        # start the mode, priority 100
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        # post event5
        self.machine.events.post('event5')
        self.advance_time_and_run()

        # led1 was red @200, mode1 is @100, so should still be red @200
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.stack[0]['priority'])
        self.assertEqual(2, len(self.machine.leds.led1.stack))

        # led2 was red @0, so now it should be orange @100
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(100, self.machine.leds.led2.stack[0]['priority'])
        self.assertEqual(2, len(self.machine.leds.led2.stack))

        # led3 was red @0, mode1 led_player has led3 @200 which should be
        # added to the mode's base priority
        self.assertEqual(list(RGBColor('orange').rgb),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(300, self.machine.leds.led3.stack[0]['priority'])
        self.assertEqual(2, len(self.machine.leds.led3.stack))

        # stop the mode, LEDs should revert
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()

        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.stack[0]['priority'])
        self.assertEqual(1, len(self.machine.leds.led1.stack))
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led2.stack[0]['priority'])
        self.assertEqual(1, len(self.machine.leds.led2.stack))
        self.assertEqual(list(RGBColor('red').rgb),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led3.stack[0]['priority'])
        self.assertEqual(1, len(self.machine.leds.led3.stack))
