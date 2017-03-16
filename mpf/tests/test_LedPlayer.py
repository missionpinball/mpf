"""Test led player."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase


class TestLedPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'led_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/led_player/'

    def test_config_player_config_processing(self):
        led1 = self.machine.lights.led1
        led2 = self.machine.lights.led2
        led3 = self.machine.lights.led3

        self.assertEqual(self.machine.config['light_player']['event1'][led1]['color'], 'red')
        self.assertEqual(self.machine.config['light_player']['event1'][led1]['fade_ms'], 0)
        self.assertEqual(self.machine.config['light_player']['event1'][led1]['priority'], 200)
        self.assertEqual(self.machine.config['light_player']['event1'][led2]['color'], 'ff0000')
        self.assertEqual(self.machine.config['light_player']['event1'][led2]['fade_ms'], 0)
        self.assertEqual(self.machine.config['light_player']['event1'][led3]['color'], 'red')
        self.assertEqual(self.machine.config['light_player']['event1'][led3]['fade_ms'], 0)

        self.assertEqual(self.machine.config['light_player']['event2'][led1]['color'], 'blue')
        self.assertEqual(self.machine.config['light_player']['event2'][led1]['fade_ms'], 200)
        self.assertEqual(self.machine.config['light_player']['event2'][led1]['priority'], 100)
        self.assertEqual(self.machine.config['light_player']['event2'][led2]['color'], 'blue')
        self.assertEqual(self.machine.config['light_player']['event2'][led2]['fade_ms'], 200)
        self.assertEqual(self.machine.config['light_player']['event2'][led1]['priority'], 100)

        self.assertEqual(self.machine.config['light_player']['event3'][led1]['color'], 'lime')
        self.assertEqual(self.machine.config['light_player']['event3'][led1]['fade_ms'], 500)
        self.assertEqual(self.machine.config['light_player']['event3'][led2]['color'], 'lime')
        self.assertEqual(self.machine.config['light_player']['event3'][led2]['fade_ms'], 500)
        self.assertEqual(self.machine.config['light_player']['event3'][led3]['color'], '00ff00')
        self.assertEqual(self.machine.config['light_player']['event3'][led3]['fade_ms'], 500)

        self.assertEqual(self.machine.config['light_player']['event4'][led1]['color'], '00ffff')
        self.assertEqual(self.machine.config['light_player']['event4'][led1]['fade_ms'], None)
        self.assertEqual(self.machine.config['light_player']['event4'][led2]['color'], '00ffff')
        self.assertEqual(self.machine.config['light_player']['event4'][led2]['fade_ms'], None)

    def test_led_player(self):
        # led_player just sets these colors and that's it.
        self.machine.events.post('event1')
        self.advance_time_and_run(1)
        self.assertLightColor("led1", 'red')
        self.assertEqual(200, self.machine.lights.led1.stack[0]['priority'])

        self.assertLightColor("led2", 'ff0000')
        self.assertEqual(0, self.machine.lights.led2.stack[0]['priority'])

        self.assertLightColor("led3", 'red')
        self.assertEqual(0, self.machine.lights.led3.stack[0]['priority'])

        # should stay in this state forever
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertLightColor("led1", 'red')
        self.assertEqual(200, self.machine.lights.led1.stack[0]['priority'])

        # test tags and fade in expanded config

        # post event2, which is a tag with led1 and led2, but at priority 100
        # led1 should remain unchanged since it was set at priority 200,
        # led2 should fade to blue since it was red before at priority 0
        self.machine.events.post('event2')
        self.advance_time_and_run(.1)

        self.assertLightColor("led1", 'red')
        self.assertEqual(200, self.machine.lights.led1.stack[0]['priority'])

        # fade is half way from red to blue
        self.assertLightColor("led2", [128, 0, 127])
        self.assertEqual(100, self.machine.lights.led2.stack[0]['priority'])

        self.advance_time_and_run()

        # fade is done
        self.assertLightColor("led2", 'blue')

        # reset leds
        self.machine.lights.led1.clear_stack()
        self.machine.lights.led2.clear_stack()
        self.machine.lights.led3.clear_stack()
        self.advance_time_and_run()

        self.assertLightColor("led1", 'off')
        self.assertFalse(self.machine.lights.led1.stack)

        self.assertLightColor("led2", 'off')
        self.assertFalse(self.machine.lights.led2.stack)

        self.assertLightColor("led3", 'off')
        self.assertFalse(self.machine.lights.led3.stack)

        # test fades via express config with a few different options
        self.machine.events.post('event3')

        # fades are 500ms, so advance 250 and check
        self.advance_time_and_run(.26)
        self.assertLightColor("led1", [0, 132, 0])
        self.assertLightColor("led2", [0, 132, 0])
        self.assertLightColor("led3", [0, 132, 0])

        # finish the fade
        self.advance_time_and_run()
        self.assertLightColor("led1", [0, 255, 0])
        self.assertLightColor("led2", [0, 255, 0])
        self.assertLightColor("led3", [0, 255, 0])

        # reset leds
        self.machine.lights.led1.clear_stack()
        self.machine.lights.led2.clear_stack()
        self.machine.lights.led3.clear_stack()
        self.advance_time_and_run()

        # tag1 is led1 and led2
        self.machine.events.post('event4')
        self.advance_time_and_run()

        self.assertLightColor("led1", [0, 255, 255])
        self.assertLightColor("led2", [0, 255, 255])
        self.assertLightColor("led3", 'off')
        self.assertLightColor("led3", 'off')

        # test led5 with default color red
        self.assertLightColor("led5", 'off')

        self.post_event("event5")
        self.advance_time_and_run()
        self.assertLightColor("led5", 'red')

    def test_single_step_show(self):
        # with single step shows, loops are automatically set to 0, hold is
        # automatically set to true

        self.machine.shows['show1'].play()
        self.advance_time_and_run()

        self.assertLightColor("led1", 'red')

        # when a show ends with hold, the final step of the show will cache
        # the led settings
        self.assertEqual(RGBColor('red'),
                         self.machine.lights.led1.stack[0]['color'])
        self.assertEqual(0, self.machine.lights.led1.stack[0]['priority'])

    def test_show_hold_leds(self):
        self.machine.shows['show2_stay_on'].play(loops=0)
        self.advance_time_and_run()

        self.assertLightColor("led1", 'red')

        self.assertEqual(RGBColor('red'),
                         self.machine.lights.led1.stack[0]['color'])
        self.assertEqual(0, self.machine.lights.led1.stack[0]['priority'])

    def test_show_no_hold_leds(self):
        show = self.machine.shows['show2'].play(loops=0)
        self.advance_time_and_run(.1)

        # led should be red while show is running
        self.assertLightColor("led1", 'red')

        self.advance_time_and_run()

        # led should be off when show ends
        self.assertLightColor("led1", 'off')
        self.assertFalse(self.machine.lights.led1.stack)

    def test_show_same_priority(self):
        # start show2, leds are red
        self.machine.shows['show2'].play()
        self.advance_time_and_run(.5)

        self.assertLightColor("led1", 'red')

        # start show3 at same priority, leds should be blue
        self.machine.shows['show3'].play()
        # timing is 600ms after show2 start, since show2 will set them to red
        # again
        self.advance_time_and_run(.1)

        self.assertLightColor("led1", 'blue')

    def test_show_higher_priority(self):
        # start show2, leds are red

        self.machine.shows['show2'].play()
        self.advance_time_and_run(.5)

        self.assertLightColor("led1", 'red')

        # start show3 at same priority, leds should be blue
        show3 = self.machine.shows['show3'].play(priority=100)
        # timing is 600ms after show2 start, since show2 will set them to red
        # again
        self.advance_time_and_run(.1)

        self.assertLightColor("led1", 'blue')

        # stop show3, leds should go back to red
        show3.stop()
        self.advance_time_and_run(.1)
        self.assertLightColor("led1", 'red')

        # and they should stay red
        self.advance_time_and_run(.5)
        self.assertLightColor("led1", 'red')

    def test_led_player_in_mode(self):
        # post event1 to get the leds set in the base config
        self.machine.events.post('event1')
        self.advance_time_and_run()

        self.assertLightColor("led1", 'red')
        self.assertLightColor("led2", 'red')
        self.assertLightColor("led3", 'red')

        # post event5, nothing should change
        self.machine.events.post('event5')
        self.advance_time_and_run()

        self.assertLightColor("led1", 'red')
        self.assertEqual(200, self.machine.lights.led1.stack[0]['priority'])
        self.assertLightColor("led2", 'red')
        self.assertEqual(0, self.machine.lights.led2.stack[0]['priority'])
        self.assertLightColor("led3", 'red')
        self.assertEqual(0, self.machine.lights.led3.stack[0]['priority'])

        # start the mode, priority 100
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        # post event5
        self.machine.events.post('event5')
        self.advance_time_and_run()

        # led1 was red @200, mode1 is @100, so should still be red @200
        self.assertLightColor("led1", 'red')
        self.assertEqual(200, self.machine.lights.led1.stack[0]['priority'])
        self.assertEqual(2, len(self.machine.lights.led1.stack))

        # led2 was red @0, so now it should be orange @100
        self.assertLightColor("led2", 'orange')
        self.assertEqual(100, self.machine.lights.led2.stack[0]['priority'])
        self.assertEqual(2, len(self.machine.lights.led2.stack))

        # led3 was red @0, mode1 led_player has led3 @200 which should be
        # added to the mode's base priority
        self.assertLightColor("led3", 'orange')
        self.assertEqual(300, self.machine.lights.led3.stack[0]['priority'])
        self.assertEqual(2, len(self.machine.lights.led3.stack))

        # stop the mode, LEDs should revert
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()

        self.assertLightColor("led1", 'red')
        self.assertEqual(200, self.machine.lights.led1.stack[0]['priority'])
        self.assertEqual(1, len(self.machine.lights.led1.stack))
        self.assertLightColor("led2", 'red')
        self.assertEqual(0, self.machine.lights.led2.stack[0]['priority'])
        self.assertEqual(1, len(self.machine.lights.led2.stack))
        self.assertLightColor("led3", 'red')
        self.assertEqual(0, self.machine.lights.led3.stack[0]['priority'])
        self.assertEqual(1, len(self.machine.lights.led3.stack))
