# mpf.tests.test_Fast_Exp

from mpf.core.rgb_color import RGBColor
from mpf.tests.test_Fast import TestFastBase


class TestFastExp(TestFastBase):
    """Tests the FAST EXP boards."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net2', 'exp']

    def get_config_file(self):
        return 'exp.yaml'

    def create_expected_commands(self):
        # These are all the defaults based on the config file for this test.
        # Individual tests can override / add as needed

        self.serial_connections['exp'].expected_commands = {'RA@880:000000': '',
                                                            'RA@881:000000': '',
                                                            'RA@882:000000': '',
                                                            'RA@890:000000': '',
                                                            'RA@892:000000': '',
                                                            'RA@B40:000000': '',
                                                            'RA@840:000000': '',
                                                            'RA@841:000000': '',
                                                            'RA@480:000000': '',
                                                            'RA@481:000000': '',
                                                            'RA@482:000000': '',
                                                            'RF@89:5DC': '',
                                                            'EM@B40:0,1,7D0,1F4,9C4,5DC': '',
                                                            'EM@B40:1,1,7D0,3E8,7D0,5DC': '',
                                                            'EM@882:7,1,7D0,3E8,7D0,5DC': '',
                                                            'MP@B40:0,7F,7D0': '',
                                                            'MP@B40:1,7F,7D0': '',
                                                            'MP@882:7,7F,7D0': '',}

    def test_servo(self):
        # go to min position
        self.exp_cpu.expected_commands = {
                "MP@B40:0,00,7D0": ""                    # MP:<INDEX>,<POSITION>,<TIME_MS><CR>
        }
        self.machine.servos["servo1"].go_to_position(0)
        self.advance_time_and_run(1)
        self.assertFalse(self.exp_cpu.expected_commands)

        # go to max position
        self.exp_cpu.expected_commands = {
                "MP@B40:0,FF,7D0": ""
        }
        self.machine.servos["servo1"].go_to_position(1)
        self.advance_time_and_run(.1)
        self.assertFalse(self.exp_cpu.expected_commands)

    def test_leds(self):

        # create local references to all the lights so they can be accessed like `led1.on()`
        for led_name, led_obj in self.machine.lights.items():
            setattr(self, led_name, led_obj)

        self.fast_exp_leds = self.machine.default_platform.fast_exp_leds

        self._test_led_internals()
        self._test_led_colors()
        self._test_exp_board_reset()
        self._test_grb_led()
        self._test_rgbw_leds()
        self._test_led_channels()
        self._test_led_software_fade()
        self._test_lew_hardware_fade()

    def _test_led_internals(self):

        # Make sure the internal LED map is correct
        self.assertIn("88100", self.fast_exp_leds)
        self.assertIn("88001", self.fast_exp_leds)
        self.assertIn("88002", self.fast_exp_leds)
        self.assertIn("88120", self.fast_exp_leds)
        self.assertIn("88121", self.fast_exp_leds)
        self.assertIn("89200", self.fast_exp_leds)

        # Make sure all the RGBW, channels, previous, and start_channels are working
        self.assertEqual(self.led22.hw_drivers['red'][0].number, '48002-0')
        self.assertEqual(self.led22.hw_drivers['green'][0].number, '48002-1')
        self.assertEqual(self.led22.hw_drivers['blue'][0].number, '48002-2')
        self.assertEqual(self.led23.hw_drivers['red'][0].number, '48003-0')
        self.assertEqual(self.led23.hw_drivers['green'][0].number, '48003-1')
        self.assertEqual(self.led23.hw_drivers['blue'][0].number, '48003-2')
        self.assertEqual(self.led24.hw_drivers['red'][0].number, '48004-0')
        self.assertEqual(self.led24.hw_drivers['green'][0].number, '48004-1')
        self.assertEqual(self.led24.hw_drivers['blue'][0].number, '48004-2')
        self.assertEqual(self.led24.hw_drivers['white'][0].number, '48005-0')
        self.assertEqual(self.led25.hw_drivers['red'][0].number, '48005-1')
        self.assertEqual(self.led25.hw_drivers['green'][0].number, '48005-2')
        self.assertEqual(self.led25.hw_drivers['blue'][0].number, '48006-0')
        self.assertEqual(self.led25.hw_drivers['white'][0].number, '48006-1')
        self.assertEqual(self.led26.hw_drivers['red'][0].number, '48006-2')
        self.assertEqual(self.led26.hw_drivers['green'][0].number, '48007-0')
        self.assertEqual(self.led26.hw_drivers['blue'][0].number, '48007-1')
        self.assertEqual(self.led26.hw_drivers['white'][0].number, '48007-2')
        self.assertEqual(self.led27.hw_drivers['red'][0].number, '48008-0')
        self.assertEqual(self.led27.hw_drivers['green'][0].number, '48008-1')
        self.assertEqual(self.led27.hw_drivers['blue'][0].number, '48008-2')
        self.assertEqual(self.led28.hw_drivers['red'][0].number, '88222-0')
        self.assertEqual(self.led28.hw_drivers['green'][0].number, '88222-1')
        self.assertEqual(self.led28.hw_drivers['blue'][0].number, '88222-2')
        self.assertEqual(self.led28.hw_drivers['white'][0].number, '88223-0')
        self.assertEqual(self.led29.hw_drivers['red'][0].number, '48009-0')
        self.assertEqual(self.led29.hw_drivers['green'][0].number, '48009-2')
        self.assertEqual(self.led29.hw_drivers['blue'][0].number, '48009-1')
        self.assertEqual(self.led29.hw_drivers['white'][0].number, '4800A-2')

    def _test_led_colors(self):

        self.exp_cpu.expected_commands = {
            'RD@880:0201ff123402121212': '',
            'RD@881:0100ffffff': '',
            'RD@841:0160ffffff': ','}

        self.led1.on()
        self.led2.color("ff1234")
        self.led3.color("121212")
        self.led19.color("ffffff")  # Verifies that ports 5-8 of the EXP-0081 are using breakout address 1 LED range 00-7F
        self.advance_time_and_run()

        self.assertEqual("FFFFFF", self.exp_cpu.leds['led1'])
        self.assertEqual("121212", self.exp_cpu.leds['led3'])
        self.assertEqual("FFFFFF", self.exp_cpu.leds['led19'])
        self.assertFalse(self.exp_cpu.expected_commands)

        # turn on a LED on a different board that has a hex index too
        self.exp_cpu.expected_commands = {'RD@B40:016affffff': '',}
        self.led18.on()
        self.advance_time_and_run()
        self.assertEqual("FFFFFF", self.exp_cpu.leds['led18'])

        # # test led off
        self.exp_cpu.expected_commands = {'RD@881:0100000000': '',}
        self.led1.off()
        self.advance_time_and_run()
        self.assertEqual("000000", self.exp_cpu.leds['led1'])

        # # test led color
        self.exp_cpu.expected_commands = {'RD@890:010002172a': '',}
        self.led7.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("02172A", self.exp_cpu.leds['led7'])

    def _test_exp_board_reset(self):
        # verify a board reset turns off the LEDs only on the board addresses

        self.exp_cpu.expected_commands = {
            'RD@881:0100ff1234': '',
            'RD@880:0102467fff': '',
            'RD@B40:016a6a6a6a': '',}

        self.led1.color("ff1234")
        self.led3.color("467fff")
        self.led18.color("6a6a6a")
        self.advance_time_and_run()

        self.exp_cpu.write(b'BR@B40:')
        self.advance_time_and_run()

        self.assertEqual("000000", self.exp_cpu.leds['led18'])  # this is on the active board and should be off
        self.assertEqual("FF1234", self.exp_cpu.leds['led1'])  # this is on a non-active board ans should still be on
        self.assertEqual("467FFF", self.exp_cpu.leds['led3'])

    def _test_grb_led(self):
        # test led10 grb
        self.exp_cpu.expected_commands = {'RD@B40:014212ff34': '',}
        self.led10.color("ff1234")
        self.advance_time_and_run()
        self.assertEqual("12FF34", self.exp_cpu.leds['led10'])  # ensure the hardware received the colors in RGB order

    def _test_rgbw_leds(self):
        self.exp_cpu.expected_commands = {'RD@480:02050000000600ff00': '',}
        self.led25.color("ffffff")
        self.advance_time_and_run()

        self.exp_cpu.expected_commands = {'RD@882:022200112223110000': '',}
        self.led28.color("112233")
        self.advance_time_and_run()

    def _test_led_channels(self):
        # LED 29 has random ordered channels
        # red 48009-0, green 48009-2, blue 48009-1, white 48010-2

        # white = 00 00 00 FF which becomes
        # 09 [00 00 00] 0A [00 00 FF]
        self.exp_cpu.expected_commands = {'RD@480:02090000000a0000ff': '',}
        self.led29.color("ffffff")
        self.advance_time_and_run()

        self.exp_cpu.expected_commands = {'RD@480:02090022110a000022': '',}
        self.led29.color("223344")  # -> 00112222
        self.advance_time_and_run()

    def _test_led_software_fade(self):

        self.exp_cpu.expected_commands = {'RD@B40:0169151515': '',
                                          'RD@B40:01692b2b2b': '',
                                          'RD@B40:0169424242': '',
                                          'RD@B40:0169585858': '',
                                          'RD@B40:0169646464': '',}

        self.led17.color(RGBColor((100, 100, 100)), fade_ms=150)
        self.advance_time_and_run(.04)
        self.assertTrue(10 < int(self.exp_cpu.leds['led17'][0:2], 16) < 40)
        self.advance_time_and_run(.04)
        self.assertTrue(30 < int(self.exp_cpu.leds['led17'][0:2], 16) < 60)
        self.advance_time_and_run(.04)
        self.assertTrue(60 < int(self.exp_cpu.leds['led17'][0:2], 16) < 90)
        self.advance_time_and_run(2)
        self.assertEqual("646464", self.exp_cpu.leds['led17'])

    def _test_lew_hardware_fade(self):
        # This is also tested via the config file and the expected commands
        self.exp_cpu.expected_commands = {'RF@88:3E8': '',}
        self.machine.default_platform.exp_boards_by_name["brian"].set_led_fade(1000)
        self.advance_time_and_run()