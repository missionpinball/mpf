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

        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led1]['color'], 'green')
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led1]['fade_ms'], 500)
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led2]['color'], 'green')
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led2]['fade_ms'], 500)
        self.assertEqual(self.machine.config['led_player']['event3']['leds'][led3]['color'], 'green')
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

        # should stay in this state forever
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)

        # post event2, which is a tag with led1 and led2, but at priority 200
        # led1 should remain unchanged, led2 should be blue
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self.assertEqual(RGBColor('red'),
                         self.machine.leds.led1.hw_driver.current_color)
        self.assertEqual(200, self.machine.leds.led1.state['priority'])
        self.assertEqual(RGBColor('blue'),
                         self.machine.leds.led2.hw_driver.current_color)
        self.assertEqual(100, self.machine.leds.led2.state['priority'])

        # todo test fades

    def test_led_player_in_show(self):
        # todo
        pass