from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, test_config, expect_startup_error

from mpf.tests.loop import MockSerial
from mpf.tests.test_Fast import BaseMockFast, MockFastNet

class MockFastExp(BaseMockFast):
    def __init__(self):
        super().__init__()
        self.type = "EXP"
        # self.ignore_commands["L1:23,FF"] = True
        self.leds = dict()  #
        self.active_board = None
        self.cmd_stack = list()

    def _parse(self, cmd):

        self.cmd_stack.append(cmd)

        cmd, payload = cmd.split(":", 1)

        if '@' in cmd:
            cmd, self.active_board = cmd.split("@", 1)

        if cmd == "EA":
            self.active_board = payload.upper()
            return True

        elif cmd == "ID":
            self.queue.append("ID:EXP FP-EXP-0201  0.5")
            # TODO where do we store different ones for different boards?
            return True

        elif cmd == "RD":
            # RD:<COUNT><INDEX>{<R><G><B>...}
            pass

            # payload is binary bytes

    def _handle_msg(self, msg):
        msg_len = len(msg)
        cmd = msg.decode()
        # strip newline
        # ignore init garbage
        if cmd == (' ' * 256 * 4):
            return msg_len

        if cmd in self.ignore_commands:
            self.queue.append(cmd[:3] + "P")
            return msg_len

        if self._parse(cmd):
            return msg_len

        if cmd in self.expected_commands:
            if self.expected_commands[cmd]:
                self.queue.append(self.expected_commands[cmd])
            del self.expected_commands[cmd]
            return msg_len
        else:
            raise Exception("Unexpected command for " + self.type + ": " + str(cmd))


class TestFastBase(MpfTestCase):
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
        self.net_cpu = MockFastNet()
        self.exp_cpu = MockFastExp()

    def create_expected_commands(self):

        self.net_cpu.expected_commands = {
            'BR:': '#!B:02',    # there might be some garbage in front of the command
            'ID:': f'ID:{self.net_cpu.id}',
            f'CH:{self.net_cpu.ch},FF': 'CH:P',
            "SA:": f"SA:{self.net_cpu.sa}",
            **self.net_cpu.attached_boards,
        }

        self.exp_cpu.expected_commands = {
            'ID:': 'ID:EXP FP-EXP-0201 0.5',
            "BR:": "BR:P",
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
            self.advance_time_and_run(0.1)

    # def test_servo(self):
    #     # go to min position
    #     self.exp_cpu.expected_commands = {
    #             "XO:03,00": "XO:P"
    #     }
    #     self.machine.servos["servo1"].go_to_position(0)
    #     self.advance_time_and_run(.1)
    #     self.assertFalse(self.net_cpu.expected_commands)

    #     # go to max position
    #     self.exp_cpu.expected_commands = {
    #             "XO:03,FF": "XO:P"
    #     }
    #     self.machine.servos["servo1"].go_to_position(1)
    #     self.advance_time_and_run(.1)
    #     self.assertFalse(self.exp_cpu.expected_commands)

    def test_leds(self):
        self._test_led()

    def _test_led(self):

        platform = self.machine.default_platform

        self.advance_time_and_run()
        led1 = self.machine.lights["led1"]
        led2 = self.machine.lights["led2"]

        self.assertIn("88000", platform.fast_exp_leds)
        self.assertIn("88001", platform.fast_exp_leds)
        self.assertIn("88004", platform.fast_exp_leds)
        self.assertIn("88121", platform.fast_exp_leds)
        self.assertIn("88122", platform.fast_exp_leds)

        # check to make sure everything is getting set up properly
        self.assertTrue(platform.exp_connection)
        self.assertTrue(platform._exp_led_task)
        # self.assertEqual(len(platform.fast_exp_leds), 5)
        self.assertTrue(platform.flag_exp_led_tick_registered)  # bool

        self.assertIn('88', platform.exp_boards)

        # self.assertTrue(platform.exp_dirty_led_ports)  # dirty on startup

        # FastExpansionBoard

        board = platform.exp_boards['88']

        board.communicator
        board.address
        board.product_id
        board.firmware_version
        board.breakouts  # list() # check that it's 4 and contains brk objects

        # FastBreakoutBoard

        brk = platform.exp_boards['88'].breakouts[0]
        brk.expansion_board
        brk.index
        brk.led_ports  # dict()
        brk.address

        # FastLEDPort

        port = platform.exp_boards['88'].breakouts[0].led_ports[0]

        # this is zero so far

        # port.breakout
        # port.address
        # port.index
        # port.leds
        # port.dirty
        # port.lowest_dirty_led
        # port.highest_dirty_led


        # self.assertEqual("000000", self.exp_cpu.leds['exp-0201-i0-b0-p1-1'])
        # self.assertEqual("000000", self.exp_cpu.leds['exp-0201-i0-b0-p2-1'])
        # test led on
        led1.on()
        self.advance_time_and_run(1)
        self.assertEqual("ffffff", self.exp_cpu.leds['97'])
        self.assertEqual("000000", self.exp_cpu.leds['98'])

        device2.color("001122")

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.exp_cpu.leds['97'])
        self.assertEqual("001122", self.exp_cpu.leds['98'])

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("02172a", self.exp_cpu.leds['97'])

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.exp_cpu.leds['97'])

        self.advance_time_and_run(.02)

        # fade led over 100ms
        device.color(RGBColor((100, 100, 100)), fade_ms=100)
        self.advance_time_and_run(.03)
        self.assertTrue(10 < int(self.exp_cpu.leds['97'][0:2], 16) < 40)
        self.assertTrue(self.exp_cpu.leds['97'][0:2] == self.exp_cpu.leds['97'][2:4] == self.exp_cpu.leds['97'][4:6])
        self.advance_time_and_run(.03)
        self.assertTrue(40 < int(self.exp_cpu.leds['97'][0:2], 16) < 60)
        self.assertTrue(self.exp_cpu.leds['97'][0:2] == self.exp_cpu.leds['97'][2:4] == self.exp_cpu.leds['97'][4:6])
        self.advance_time_and_run(.03)
        self.assertTrue(60 < int(self.exp_cpu.leds['97'][0:2], 16) < 90)
        self.assertTrue(self.exp_cpu.leds['97'][0:2] == self.exp_cpu.leds['97'][2:4] == self.exp_cpu.leds['97'][4:6])
        self.advance_time_and_run(2)
        self.assertEqual("646464", self.exp_cpu.leds['97'])
