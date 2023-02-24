from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, test_config, expect_startup_error

from mpf.tests.loop import MockSerial
from mpf.tests.test_Fast import BaseMockFast, MockFastNetNeuron


class MockFastExp(BaseMockFast):
    def __init__(self, test_fast_base):
        super().__init__()
        self.test_fast_base = test_fast_base
        self.type = "EXP"
        # self.ignore_commands["L1:23,FF"] = True
        self.leds = dict()  #
        self.active_board = None
        self.cmd_stack = list()  # list of commands received, e.g. ['ID:', 'ID@88:', 'ID@89:', 'EA:880', 'RD:0200ffffff121212']
        self.led_map = dict()  # LED number to name index, e.g. 88000: "led1", 88121: "led5"

    def _parse(self, cmd):
        # returns True if the command was handled, False if it was not

        self.cmd_stack.append(cmd)

        cmd, payload = cmd.split(":", 1)

        if '@' in cmd:
            cmd, temp_active = cmd.split("@", 1)

        elif cmd == "EA":
            temp_active = self.active_board = payload.upper()
            return True

        else:
            temp_active = self.active_board

        if cmd == "ID":

            if temp_active in ["88", "89", "8A", "8B"]:  # 201
                self.queue.append("ID:EXP FP-EXP-0201  0.8")

            elif temp_active in ["B4", "B5", "B6", "B7"]:  # 71
                self.queue.append("ID:EXP FP-EXP-0071  0.8")

            elif temp_active in ["84", "85", "86", "87"]:  # 71
                self.queue.append("ID:EXP FP-EXP-0081  0.8")

            elif temp_active == '48':  # Neuron
                self.queue.append("ID:EXP FP-CPU-2000 0.8")

            if not temp_active:  # no ID has been set, so lowest address will respond
                self.queue.append("ID:EXP FP-CPU-2000 0.8")

            return True

        elif cmd == "BR":
            # turn off all the LEDs on that board
            for led_number, led_name in self.led_map.items():
                if led_number.startswith(temp_active):
                    self.leds[led_name] = "000000"

            self.queue.append("BR:P")
            return True

        elif cmd == "RD":
            # RD:<COUNT>{<INDEX><R><G><B>...}

            # 88120

            self.test_fast_base.assertTrue(self.active_board, "Received RD: command with no active expansion board set")

            if not self.led_map:
                for name, led in self.test_fast_base.machine.lights.items():
                    led_number = led.hw_drivers['red'][0].number.split('-')[0]  # 88000
                    self.led_map[led_number] = name

            count = int(payload[:2], 16)
            color_data = payload[2:]

            assert len(color_data) == count * 8

            # update our record of the LED colors
            for i in range(count):
                color = color_data[i * 8 + 2:i * 8 + 8]
                led_number = f'{self.active_board}{color_data[i * 8:i * 8 + 2]}'.upper()

                self.leds[self.led_map[led_number]] = color

            return True

        elif cmd in ["EM", "MP"]:
            return True

        return False

    def _handle_msg(self, msg):
        msg_len = len(msg)

        try:
            cmd = msg.decode()
        except UnicodeDecodeError:
            # binary message. The first three chars are the command, the rest is the binary payload
            cmd = f'{msg[:3].decode()}{msg[3:].hex()}'

        if cmd in self.ignore_commands:
            # self.queue.append(cmd[:3] + "P")
            return msg_len

        if self._parse(cmd):
            return msg_len

        elif cmd in self.expected_commands:
            if self.expected_commands[cmd]:
                self.queue.append(self.expected_commands[cmd])
            del self.expected_commands[cmd]
            return msg_len

        else:
            raise Exception("Unexpected command for " + self.type + ": " + str(cmd))

    # def send(self, msg):
    #     if not self.is_open:
    #         raise AssertionError("Serial not open")

    #     return self.write(msg.encode() + b'\r')

    # def write(self, msg):
    #     """Write message."""

    #     # TODO this is an example of how it come in which we might need to handle
    #     # b'EA:880\rRD:\x02\x00\xff\xff\xff\x12\x12\x12'

    #     ignored_parts = [b' ' * 1024, b'']

    #     parts = msg.split(b'\r')
    #     # assert parts.pop() == b''
    #     for part in parts:
    #         if part in ignored_parts:
    #             continue
    #         self._handle_msg(part)

    #     return len(msg)


class TestFastExp(MpfTestCase):
    """Base class for FAST platform tests, using a default V2 network."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.net_cpu = None
        self.exp_cpu = None

    def get_config_file(self):
        return 'config_exp.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/fast/'

    def get_platform(self):
        return False

    def _mock_loop(self):
        if self.net_cpu:
            self.clock.mock_serial("com3", self.net_cpu)
        if self.exp_cpu:
            self.clock.mock_serial("com4", self.exp_cpu)

    def create_connections(self):
        self.net_cpu = MockFastNetNeuron()
        self.exp_cpu = MockFastExp(self)

    def create_expected_commands(self):

        self.net_cpu.expected_commands = {
            # 'BR:': '#!B:02',    # there might be some garbage in front of the command
            'ID:': f'ID:{self.net_cpu.id}',
            f'CH:{self.net_cpu.ch},FF': 'CH:P',
            "SA:": f"SA:{self.net_cpu.sa}",
            **self.net_cpu.attached_boards,
        }

    def tearDown(self):
        if self.net_cpu:
            self.net_cpu.expected_commands = {
                "WD:1": "WD:P"
            }
        if self.exp_cpu:
            self.exp_cpu.expected_commands = {
            }

        super().tearDown()
        if not self.startup_error:
            self.assertFalse(self.net_cpu and self.net_cpu.expected_commands)
            self.assertFalse(self.exp_cpu and self.exp_cpu.expected_commands)

    def setUp(self):
        self.expected_duration = 2
        self.create_connections()
        self.create_expected_commands()
        super().setUp()

        # If a test is testing a bad config file and causes a startup exception,
        # the machine will shut down. Safety check before we add futures to the loop.
        if not self.machine.is_shutting_down:
            # There are startup calls that keep the serial traffic busy. Many tests define
            # self.net_cpu.expected_commands assuming that the serial bus is quiet. Add a
            # tiny delay here to let the startup traffic clear out so that tests don't get
            # slammed with unexpected network traffic.
            # Note that the above scenario only causes tests to fail on Windows machines!

            # These startup calls simulate some delay in response, so we need to wait the full
            # second below. This might need to be increased if there's lots of hardware.
            self.advance_time_and_run(1)

    def test_servo(self):
        # go to min position
        self.exp_cpu.expected_commands = {
                "EM@84:0,1,07D0,01F4,07D0,05DC": "",  # EM:<INDEX>,1,<MAX_TIME_MS>,<MIN_US>,<MAX_US>,<NEUTRAL_US><CR>  1 = servo
                "MP@84:0,00": ""                    # MP:<INDEX>,<POSITION>,<TIME_MS><CR>
        }
        self.machine.servos["servo1"].go_to_position(0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # go to max position
        self.exp_cpu.expected_commands = {
                "MP@84:0,FF": ""
        }
        self.machine.servos["servo1"].go_to_position(1)
        self.advance_time_and_run(.1)
        self.assertFalse(self.exp_cpu.expected_commands)

    def test_leds(self):
        self._test_led()

    def _test_led(self):

        platform = self.machine.default_platform

        self.advance_time_and_run(1)

        # create local references to all the lights
        for led_name, led_obj in self.machine.lights.items():
            globals()[led_name] = led_obj

        self.assertIn("88000", platform.fast_exp_leds)
        self.assertIn("88001", platform.fast_exp_leds)
        self.assertIn("88002", platform.fast_exp_leds)
        self.assertIn("88120", platform.fast_exp_leds)
        self.assertIn("88121", platform.fast_exp_leds)
        self.assertIn("89200", platform.fast_exp_leds)

        # check to make sure everything is getting set up properly
        self.assertTrue(platform.exp_connection)
        self.assertTrue(platform._exp_led_task)
        # self.assertEqual(len(platform.fast_exp_leds), 5)
        self.assertTrue(platform.flag_exp_led_tick_registered)  # bool

        self.assertIn('88', platform.exp_boards_by_address)

        led1.on()
        led2.color("ff1234")
        led3.color("121212")
        self.advance_time_and_run()
        self.assertEqual("ffffff", self.exp_cpu.leds['led1'])
        self.assertEqual("121212", self.exp_cpu.leds['led3'])

        # verify we got a color command for just these two without the one in the middle
        self.assertIn('RD:0300ffffff01ff123402121212', self.exp_cpu.cmd_stack)

        # turn on a LED on a different board that has a hex index too
        led18.on()
        self.advance_time_and_run()
        self.assertEqual("ffffff", self.exp_cpu.leds['led18'])

        self.assertIn('RD:016affffff', self.exp_cpu.cmd_stack) # verifies that a non-zero LED does not include all the lower index ones.
        # This is what we don't want: 'RD:0b60000000000000000000000000000000000000000000000000000000000000ffffff'

        # verify a board reset turns off the LEDs only on the current active board
        self.exp_cpu.send("BR:")
        self.advance_time_and_run()
        self.assertEqual("000000", self.exp_cpu.leds['led18'])  # this is on the active board and should be off
        self.assertEqual("ffffff", self.exp_cpu.leds['led1'])  # this is on a non-active board ans should still be on
        self.assertEqual("121212", self.exp_cpu.leds['led3'])

        # test led10 grb
        led10.color("ff1234")
        self.advance_time_and_run()
        self.assertEqual("12ff34", self.exp_cpu.leds['led10'])  # ensure the hardware received the colors in RGB order

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
