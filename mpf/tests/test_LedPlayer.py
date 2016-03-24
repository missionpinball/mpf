from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase

from mpf.core.config_player import ConfigPlayer

class TestLedPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'led_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/led_player/'

    def test_config_player_config_processing(self):
        self.assertIn('led_player', ConfigPlayer.config_file_players)

        led1 = self.machine.leds.led1
        led2 = self.machine.leds.led2
        led3 = self.machine.leds.led3
        led4 = self.machine.leds.led4

        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led1]['color'], 'red')
        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led1]['fade_ms'], 0)
        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led1]['priority'], 200)
        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led2]['color'], 'ff0000')
        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led2]['fade_ms'], 0)
        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led3]['color'], 'red')
        self.assertEqual(self.machine.config['led_player']['event1']['leds'][led3]['fade_ms'], 0)

        self.assertEqual(self.machine.config['led_player']['event2']['leds'][led1]['color'], 'blue')
        self.assertEqual(self.machine.config['led_player']['event2']['leds'][led1]['fade_ms'], 20)
        self.assertEqual(self.machine.config['led_player']['event2']['leds'][led1]['priority'], 100)
        self.assertEqual(self.machine.config['led_player']['event2']['leds'][led2]['color'], 'blue')
        self.assertEqual(self.machine.config['led_player']['event2']['leds'][led2]['fade_ms'], 20)
        self.assertEqual(self.machine.config['led_player']['event2']['leds'][led1]['priority'], 100)

        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led1]['color'], 'lime')
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led1]['fade_ms'], 500)
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led2]['color'], 'lime')
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led2]['fade_ms'], 500)
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led3]['color'], '00ff00')
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led3]['fade_ms'], 500)

        self.assertEqual(self.machine.config['led_player']['event4']['leds'][led1]['color'], '00ffff')
        self.assertEqual(self.machine.config['led_player']['event4']['leds'][led1]['fade_ms'], 0)
        self.assertEqual(self.machine.config['led_player']['event4']['leds'][led2]['color'], '00ffff')
        self.assertEqual(self.machine.config['led_player']['event4']['leds'][led2]['fade_ms'], 0)

    def test_led_player(self):
        # led_player just sets these colors and that's it.
        self.machine.events.post('event1')
        self.advance_time_and_run(1)
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.state['priority'])

        self.assertEqual(RGBColor('ff0000'),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led2.state['priority'])

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led3.state['priority'])

        # Make sure they're cached since this is a led_player entry and not
        # from a show
        self.assertEqual(200, self.machine.leds.led1.cache['priority'])
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.cache['color'])
        self.assertEqual(0, self.machine.leds.led2.cache['priority'])
        self.assertEqual(RGBColor('ff0000'),
                         self.machine.leds.led2.cache['color'])
        self.assertEqual(0, self.machine.leds.led3.cache['priority'])
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led3.cache['color'])

        # should stay in this state forever
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.state['priority'])

        # test tags and fade in expanded config

        # post event2, which is a tag with led1 and led2, but at priority 100
        # led1 should remain unchanged since it was set at priority 200,
        # led2 should fade to blue since it was red before at priority 0
        self.machine.events.post('event2')
        self.advance_time_and_run(.01)
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.state['priority'])

        # fade is half way from red to blue
        self.assertEqual(RGBColor((128, 0, 127)),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(100, self.machine.leds.led2.state['priority'])

        self.advance_time_and_run()

        # fade is done
        self.assertEqual(RGBColor('blue'),
                         self.machine.leds.led2.hw_driver.current_color)

        # reset leds, also tests "force"
        self.machine.leds.led1.color(color='off', priority=0, force=True)
        self.machine.leds.led2.color(color='off', priority=0, force=True)
        self.machine.leds.led3.color(color='off', priority=0, force=True)

        self.assertEqual('off', self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led1.state['priority'])
        self.assertEqual('off', self.machine.leds.led1.cache['color'])
        self.assertEqual(0, self.machine.leds.led1.cache['priority'])

        self.assertEqual('off', self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led2.state['priority'])
        self.assertEqual('off', self.machine.leds.led2.cache['color'])
        self.assertEqual(0, self.machine.leds.led2.cache['priority'])

        self.assertEqual('off', self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual(0, self.machine.leds.led3.state['priority'])
        self.assertEqual('off', self.machine.leds.led3.cache['color'])
        self.assertEqual(0, self.machine.leds.led3.cache['priority'])

        # test fades via express config with a few different options
        self.machine.events.post('event3')

        # fades are 500ms, so advance 250 and check
        self.advance_time_and_run(.25)
        self.assertEqual(RGBColor((0, 127, 0)),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(RGBColor((0, 127, 0)),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(RGBColor((0, 127, 0)),
                         self.machine.leds.led3.hw_driver.current_color)

        # finish the fade
        self.advance_time_and_run()
        self.assertEqual(RGBColor((0, 255, 0)),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(RGBColor((0, 255, 0)),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(RGBColor((0, 255, 0)),
                         self.machine.leds.led3.hw_driver.current_color)

        # test tags in express format
        self.machine.leds.led1.color(color='off', priority=0, force=True)
        self.machine.leds.led2.color(color='off', priority=0, force=True)
        self.machine.leds.led3.color(color='off', priority=0, force=True)

        # tag1 is led1 and led2
        self.machine.events.post('event4')
        self.advance_time_and_run()

        self.assertEqual(RGBColor((0, 255, 255)),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(RGBColor((0, 255, 255)),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual('off',
                         self.machine.leds.led3.hw_driver.current_color)
        self.assertEqual('off',
                         self.machine.leds.led3.hw_driver.current_color)

    def test_single_step_show(self):
        # with single step shows, loops are automatically set to 0, hold is
        # automatically set to true

        self.machine.shows['show1'].play()
        self.advance_time_and_run()

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        # when a show ends with hold, the final step of the show will cache
        # the led settings
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.state['color'])
        self.assertEqual(0, self.machine.leds.led1.state['priority'])
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.cache['color'])
        self.assertEqual(0, self.machine.leds.led1.cache['priority'])

    def test_show_hold_leds(self):
        self.machine.shows['show2'].play(loops=0, hold=True)
        self.advance_time_and_run()

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.state['color'])
        self.assertEqual(0, self.machine.leds.led1.state['priority'])
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.cache['color'])
        self.assertEqual(0, self.machine.leds.led1.cache['priority'])

    def test_show_no_hold_leds(self):
        self.machine.shows['show2'].play(loops=0)
        self.advance_time_and_run(.1)

        # led should be red while show is running
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        self.advance_time_and_run()

        # led should be off when show ends
        self.assertEqual(RGBColor('off'),
                         self.machine.leds.led1.state['color'])
        self.assertEqual(0, self.machine.leds.led1.state['priority'])
        self.assertEqual(RGBColor('off'),
                         self.machine.leds.led1.cache['color'])
        self.assertEqual(0, self.machine.leds.led1.cache['priority'])

    def test_show_same_priority(self):
        # start show2, leds are red
        self.machine.shows['show2'].play()
        self.advance_time_and_run(.5)

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        # start show3 at same priority, leds should be blue
        self.machine.shows['show3'].play()
        # timing is 600ms after show2 start, since show2 will set them to red
        # again
        self.advance_time_and_run(.1)

        self.assertEqual(RGBColor('blue'),
                         self.machine.leds.led1.hw_driver.current_color)

    def test_show_higher_priority(self):
        # start show2, leds are red

        return

        # todo need to implement the config_player restore for this to work

        self.machine.shows['show2'].play()
        self.advance_time_and_run(.5)

        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        # start show3 at same priority, leds should be blue
        show3 = self.machine.shows['show3'].play(priority=100)
        # timing is 600ms after show2 start, since show2 will set them to red
        # again
        self.advance_time_and_run(.1)

        self.assertEqual(RGBColor('blue'),
                         self.machine.leds.led1.hw_driver.current_color)

        # stop show3, leds should go back to red
        show3.stop()
        self.advance_time_and_run(.1)
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        # and they should stay red
        self.advance_time_and_run(.5)
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)
