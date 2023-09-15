# mpf.tests.test_Fast_Exp

from mpf.tests.test_Fast import TestFastBase


class TestFastExp(TestFastBase):
    """Tests the FAST EXP boards."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net2', 'exp']

    def get_config_file(self):
        return 'config_exp.yaml'

    def create_expected_commands(self):
        # These are all the defaults based on the config file for this test.
        # Individual tests can override / add as needed

        self.serial_connections['net2'].expected_commands = {}
        self.serial_connections['exp'].expected_commands = {}

    def DISABLED_test_servo(self):
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
        self._test_led()

    def _test_led(self):

        platform = self.machine.default_platform

        self.advance_time_and_run(1)

        # create local references to all the lights so they can be accessed like `led1.on()`
        for led_name, led_obj in self.machine.lights.items():
            globals()[led_name] = led_obj

        self.assertIn("88100", platform.fast_exp_leds)
        self.assertIn("88001", platform.fast_exp_leds)
        self.assertIn("88002", platform.fast_exp_leds)
        self.assertIn("88120", platform.fast_exp_leds)
        self.assertIn("88121", platform.fast_exp_leds)
        self.assertIn("89200", platform.fast_exp_leds)

        exp_comm = platform.serial_connections['exp']

        self.exp_cpu.expected_commands = {
            'EA:880':'',
            'RD:0201ff123402121212':'',
            'EA:881':'',
            'RD:0100ffffff':'',
        }

        led1.on()
        led2.color("ff1234")
        led3.color("121212")
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertEqual("FFFFFF", self.exp_cpu.leds['led1'])
        self.assertEqual("121212", self.exp_cpu.leds['led3'])

        self.assertFalse(self.exp_cpu.expected_commands)

        # turn on a LED on a different board that has a hex index too
        led18.on()
        self.advance_time_and_run()
        self.assertEqual("FFFFFF", self.exp_cpu.leds['led18'])

        self.assertIn('RD:016affffff', self.exp_cpu.msg_history) # verifies that a non-zero LED does not include all the lower index ones.
        # This is what we don't want: 'RD:0b60000000000000000000000000000000000000000000000000000000000000ffffff'

        # verify a board reset turns off the LEDs only on the current active board
        self.exp_cpu.write(b'BR:')
        self.advance_time_and_run()
        self.assertEqual("000000", self.exp_cpu.leds['led18'])  # this is on the active board and should be off
        self.assertEqual("FFFFFF", self.exp_cpu.leds['led1'])  # this is on a non-active board ans should still be on
        self.assertEqual("121212", self.exp_cpu.leds['led3'])

        # test led10 grb
        led10.color("ff1234")
        self.advance_time_and_run()
        self.assertEqual("12FF34", self.exp_cpu.leds['led10'])  # ensure the hardware received the colors in RGB order

        # # test led off
        # device.off()
        # self.advance_time_and_run(1)
        # self.assertEqual("000000", self.exp_cpu.leds['97'])
        # self.assertEqual("001122", self.exp_cpu.leds['98'])

        # # test led color
        # device.color(RGBColor((2, 23, 42)))
        # self.advance_time_and_run(1)
        # self.assertEqual("02172a", self.exp_cpu.leds['97'])

        # # test led off
        # device.off()
        # self.advance_time_and_run(1)
        # self.assertEqual("000000", self.exp_cpu.leds['97'])

        # self.advance_time_and_run(.02)

        # # fade led over 100ms
        # device.color(RGBColor((100, 100, 100)), fade_ms=100)
        # self.advance_time_and_run(.03)
        # self.assertTrue(10 < int(self.exp_cpu.leds['97'][0:2], 16) < 40)
        # self.assertTrue(self.exp_cpu.leds['97'][0:2] == self.exp_cpu.leds['97'][2:4] == self.exp_cpu.leds['97'][4:6])
        # self.advance_time_and_run(.03)
        # self.assertTrue(40 < int(self.exp_cpu.leds['97'][0:2], 16) < 60)
        # self.assertTrue(self.exp_cpu.leds['97'][0:2] == self.exp_cpu.leds['97'][2:4] == self.exp_cpu.leds['97'][4:6])
        # self.advance_time_and_run(.03)
        # self.assertTrue(60 < int(self.exp_cpu.leds['97'][0:2], 16) < 90)
        # self.assertTrue(self.exp_cpu.leds['97'][0:2] == self.exp_cpu.leds['97'][2:4] == self.exp_cpu.leds['97'][4:6])
        # self.advance_time_and_run(2)
        # self.assertEqual("646464", self.exp_cpu.leds['97'])
