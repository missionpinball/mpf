from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, test_config, expect_startup_error

from mpf.tests.loop import MockSerial


class BaseMockFast(MockSerial):

    def __init__(self):
        super().__init__()
        self.type = None
        self.queue = []
        self.expected_commands = {}
        self.ignore_commands = {}

    def read(self, length):
        del length
        if not self.queue:
            return
        # msg = (self.queue.pop() + '\r').encode()

        msg = self.queue.pop()
        print(f'<<< {msg}')
        msg = (msg + '\r').encode()
        return msg

    def read_ready(self):
        return bool(len(self.queue) > 0)

    def write_ready(self):
        return True

    def _parse(self, msg):
        return False

    def write(self, msg):
        """Write message."""
        parts = msg.split(b'\r')
        # remove last newline
        assert parts.pop() == b''

        for part in parts:
            self._handle_msg(part)

        return len(msg)

    def _handle_msg(self, msg):
        msg_len = len(msg)
        cmd = msg.decode()
        print(f'>>> {cmd}')
        # strip newline
        # ignore init garbage
        if cmd == (' ' * 256 * 4):
            return msg_len

        if cmd[:3] == "WD:" and cmd != "WD:1":
            self.queue.append("WD:P")
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

    def stop(self):
        pass


class MockFastDmd(BaseMockFast):
    def __init__(self):
        super().__init__()
        self.type = "DMD"

    def write(self, msg):
        """Write message."""
        parts = msg.split(b'\r')

        # remove last newline
        if parts[len(parts) - 1] == b'':
            parts.pop()

        for part in parts:
            self._handle_msg(part)

        return len(msg)

    def _handle_msg(self, msg):
        msg_len = len(msg)
        if msg == (b' ' * 256 * 4):
            return msg_len

        cmd = msg

        if cmd[:3] == "WD:":
            self.queue.append("WD:P")
            return msg_len

        if cmd in self.ignore_commands:
            self.queue.append(cmd[:3] + "P")
            return msg_len

        if cmd in self.expected_commands:
            if self.expected_commands[cmd]:
                self.queue.append(self.expected_commands[cmd])
            del self.expected_commands[cmd]
            return msg_len
        else:
            raise Exception(self.type + ": " + str(cmd))


class MockFastRgb(BaseMockFast):
    def __init__(self):
        super().__init__()
        self.type = "RGB"
        self.ignore_commands["L1:23,FF"] = True
        self.leds = {}

    def _parse(self, cmd):
        if cmd[:3] == "RS:":
            remaining = cmd[3:]
            while True:
                self.leds[remaining[0:2]] = remaining[2:8]
                remaining = remaining[9:]

                if not remaining:
                    break

            self.queue.append("RX:P")
            return True


class MockFastNet(BaseMockFast):
    def __init__(self):
        super().__init__()
        self.type = "NET"
        self.id = "NET FP-CPU-2000  02.06"
        self.sa = "09,050000000000000000"
        self.ch = "2000"
        self.expected_commands = None

        # self.attached_boards = {
        #     'NN:00': 'NN:00,FP-I/O-3208-2   ,02.00,08,20,04,06,00,00,00,00',     # 3208 board
        #     'NN:01': 'NN:01,FP-I/O-0804-1   ,02.00,04,08,04,06,00,00,00,00',     # 0804 board
        #     'NN:02': 'NN:02,FP-I/O-1616-2   ,02.00,10,10,04,06,00,00,00,00',     # 1616 board
        #     'NN:03': 'NN:03,FP-I/O-1616-2   ,02.00,10,10,04,06,00,00,00,00',     # 1616 board
        #     'NN:04': 'NN:04,,,,,,,,,,',     # no board
        # }

        self.attached_boards = {
            'NN:00': 'NN:00,FP-I/O-3208-3   ,01.09,08,20,00,00,00,00,00,00',     # 3208 board
            'NN:01': 'NN:01,FP-I/O-0804-3   ,01.09,04,08,00,00,00,00,00,00',     # 0804 board
            'NN:02': 'NN:02,FP-I/O-1616-3   ,01.09,10,10,00,00,00,00,00,00',     # 1616 board
            'NN:03': 'NN:03,FP-I/O-1616-3   ,01.09,10,10,00,00,00,00,00,00',     # 1616 board
            'NN:04': 'NN:04,!Node Not Found!,00.00,00,00,00,00,00,00,00,00',     # no board
        }

class MockFastSeg(BaseMockFast):
    def __init__(self):
        super().__init__()
        self.type = "SEG"


class TestFastBase(MpfTestCase):
    """Base class for FAST platform tests, using a default V2 network."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.net_cpu = None
        self.seg_cpu = None
        self.rgb_cpu = None
        self.dmd_cpu = None

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/fast/'

    def get_platform(self):
        return False

    def _mock_loop(self):
        if self.net_cpu:
            self.clock.mock_serial("com4", self.net_cpu)
        if self.seg_cpu:
            self.clock.mock_serial("com3", self.seg_cpu)
        if self.rgb_cpu:
            self.clock.mock_serial("com5", self.rgb_cpu)
        if self.dmd_cpu:
            self.clock.mock_serial("com6", self.dmd_cpu)

    def create_connections(self):
        self.net_cpu = MockFastNet()
        self.rgb_cpu = MockFastRgb()
        self.dmd_cpu = MockFastDmd()
        self.seg_cpu = MockFastSeg()

    def create_expected_commands(self):
        self.net_cpu.expected_commands = {
            'BR:': '\r\r!B:00\r..!B:02\r.',
            'ID:': f'ID:{self.net_cpu.id}',
            f'CH:{self.net_cpu.ch},FF': 'CH:P',
            **self.net_cpu.attached_boards,
            "SA:": f"SA:{self.net_cpu.sa}",
            "SL:01,01,04,04": "SL:P",
            "SL:02,01,04,04": "SL:P",
            "SL:03,01,04,04": "SL:P",
            "SL:0B,01,04,04": "SL:P",
            "SL:0C,01,04,04": "SL:P",
            "SL:16,01,04,04": "SL:P",
            "SL:07,01,1A,05": "SL:P",
            "SL:1A,01,04,04": "SL:P",
            "SL:39,01,04,04": "SL:P",
            "DL:00,00,00,00": "DL:P",
            "DL:01,00,00,00": "DL:P",
            "DL:04,00,00,00": "DL:P",
            "DL:06,00,00,00": "DL:P",
            "DL:07,00,00,00": "DL:P",
            "DL:11,00,00,00": "DL:P",
            "DL:12,00,00,00": "DL:P",
            "DL:13,00,00,00": "DL:P",
            "DL:16,00,00,00": "DL:P",
            "DL:17,00,00,00": "DL:P",
            "DL:20,00,00,00": "DL:P",
            "DL:21,00,00,00": "DL:P",
            "DL:01,C1,00,18,00,FF,FF,00": "DL:P",   # configure digital output
            "XO:03,7F": "XO:P",
            "XO:14,7F": "XO:P"
        }
        self.dmd_cpu.expected_commands = {
            b'ID:': 'ID:DMD FP-CPU-002-2 00.88',
        }
        self.rgb_cpu.expected_commands = {
            'ID:': 'ID:RGB FP-CPU-002-2 00.89',
            "RF:0": "RF:P",
            "RA:000000": "RA:P",
            "RF:00": "RF:P",
        }
        self.seg_cpu.expected_commands = {
            'ID:': 'ID:SEG FP-CPU-002-2 00.10',
        }

    def tearDown(self):
        if self.dmd_cpu:
            self.dmd_cpu.expected_commands = {
                b'BL:AA55': "!SRE"
            }
        if self.rgb_cpu:
            self.rgb_cpu.expected_commands = {
                "BL:AA55": "!SRE"
            }
        if self.net_cpu:
            self.net_cpu.expected_commands = {
                "WD:1": "WD:P"
            }
        super().tearDown()
        if not self.startup_error:
            self.assertFalse(self.net_cpu and self.net_cpu.expected_commands)
            self.assertFalse(self.rgb_cpu and self.rgb_cpu.expected_commands)
            self.assertFalse(self.dmd_cpu and self.dmd_cpu.expected_commands)

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

    def test_coils(self):
        self._test_pulse()
        self._test_long_pulse()
        self._test_timed_enable()
        self._test_default_timed_enable()
        self._test_enable_exception()
        self._test_allow_enable()
        self._test_pwm_ssm()
        self._test_coil_configure()

        # test hardware scan
        info_str = """NET CPU: NET FP-CPU-2000-1 2.00
RGB CPU: RGB FP-CPU-002-2 00.89
No connection to the Audio Controller.
DMD CPU: DMD FP-CPU-002-2 00.88
Segment Controller: SEG FP-CPU-002-2 00.10
No connection to the Expansion Bus.

Boards:
Board 0 - Model: FP-I/O-3208-2    Firmware: 02.00 Switches: 32 Drivers: 8
Board 1 - Model: FP-I/O-0804-1    Firmware: 02.00 Switches: 8 Drivers: 4
Board 2 - Model: FP-I/O-1616-2    Firmware: 02.00 Switches: 16 Drivers: 16
Board 3 - Model: FP-I/O-1616-2    Firmware: 02.00 Switches: 16 Drivers: 16
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_coil_configure(self):
        self.assertEqual("FAST Board 0", self.machine.coils["c_test"].hw_driver.get_board_name())
        self.assertEqual("FAST Board 3", self.machine.coils["c_flipper_hold"].hw_driver.get_board_name())
        # last driver on board
        self.net_cpu.expected_commands = {
            "DL:2B,00,00,00": "DL:P"
        }
        coil = self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '3-15',
                                                              {"connection": "network", "recycle_ms": 10})
        self.assertEqual('2B', coil.number)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # board 0 has 8 drivers. configuring driver 9 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '0-8',
                                                           {"connection": "network", "recycle_ms": 10})

        # only boards 0-3 exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '4-0',
                                                           {"connection": "network", "recycle_ms": 10})

        # only 8 + 4 + 16 + 16 = 44 = 0x2C driver exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '44',
                                                           {"connection": "network", "recycle_ms": 10})

    def _test_pulse(self):
        self.net_cpu.expected_commands = {
            "DL:04,89,00,10,17,FF,00,00,00": "DL:P"
        }
        # pulse coil 4
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_long_pulse(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DL:12,C1,00,18,00,FF,FF,00": "DL:P"
        }
        self.machine.coils["c_long_pulse"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # disable command
        self.net_cpu.expected_commands = {
            "TL:12,02": "TL:P"
        }

        self.advance_time_and_run(1)
        # pulse_ms is 2000ms, so after 1s, this should not be sent
        self.assertTrue(self.net_cpu.expected_commands)

        self.advance_time_and_run(1)
        # but after 2s, it should be
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_timed_enable(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DL:16,89,00,10,14,FF,C8,88,00": "DL:P"
        }
        self.machine.coils["c_timed_enable"].timed_enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_default_timed_enable(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DL:17,89,00,10,14,FF,C8,88,00": "DL:P"
        }
        self.machine.coils["c_default_timed_enable"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils["c_test"].enable()
            self.advance_time_and_run(.1)

    def _test_allow_enable(self):
        self.net_cpu.expected_commands = {
            "DL:06,C1,00,18,17,FF,FF,00": "DL:P"
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_pwm_ssm(self):
        self.net_cpu.expected_commands = {
            "DL:13,C1,00,18,0A,FF,84224244,00": "DL:P"
        }
        self.machine.coils["c_hold_ssm"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_nano_reboot(self):
        # NANO reboots
        self.net_cpu.queue.append("!B:00")
        self.advance_time_and_run(.1)
        # assert that MPF will stop
        self.assertTrue(self.machine.stop_future.done())

    def test_rules(self):
        self._test_enable_exception_hw_rule()
        self._test_two_rules_one_switch()
        self._test_hw_rule_pulse()
        self._test_hw_rule_pulse_pwm32()
        self._test_hw_rule_pulse_inverted_switch()
        self._test_hw_rule_same_board()

    def _test_hw_rule_same_board(self):
        self.net_cpu.expected_commands = {
            "DL:21,01,07,10,0A,FF,00,00,14": "DL:P"
        }
        # coil and switch are on different boards but first 8 switches always work
        self.machine.autofire_coils["ac_different_boards"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # switch and coil on board 3. should work
        self.net_cpu.expected_commands = {
            "DL:21,01,39,10,0A,FF,00,00,14": "DL:P",
            "SL:39,01,02,02": "SL:P"
        }
        self.machine.autofire_coils["ac_board_3"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DL:21,01,16,10,0A,FF,00,00,14": "DL:P",
        }
        # coil and switch are on different boards
        self.machine.autofire_coils["ac_broken_combination"].enable()
        self.advance_time_and_run(.1)

    def _test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.flippers["f_test_single"].config['main_coil_overwrite']['hold_power'] = 1.0
            self.machine.flippers["f_test_single"].enable()

        self.machine.flippers["f_test_single"].config['main_coil_overwrite']['hold_power'] = None

    def _test_two_rules_one_switch(self):
        self.net_cpu.expected_commands = {
            "SL:03,01,02,02": "SL:P",
            "DL:04,01,03,10,17,FF,00,00,1B": "DL:P",
            "DL:06,01,03,10,17,FF,00,00,2E": "DL:P"
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse(self):
        self.net_cpu.expected_commands = {
            "DL:07,01,16,10,0A,FF,00,00,14": "DL:P",  # hw rule
            "SL:16,01,02,02": "SL:P"                  # debounce quick on switch
        }
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DL:07,81": "DL:P"
        }
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_pwm32(self):
        self.net_cpu.expected_commands = {
            "DL:11,89,00,10,0A,AAAAAAAA,00,00,00": "DL:P"
        }
        self.machine.coils["c_pulse_pwm32_mask"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DL:11,C1,00,18,0A,AAAAAAAA,4A4A4A4A,00": "DL:P"
        }
        self.machine.coils["c_pulse_pwm32_mask"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.net_cpu.expected_commands = {
            "DL:07,11,1A,10,0A,FF,00,00,14": "DL:P",
            "SL:1A,01,02,02": "SL:P"
        }
        self.machine.autofire_coils["ac_inverted_switch"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_servo(self):
        # go to min position
        self.net_cpu.expected_commands = {
                "XO:03,00": "XO:P"
        }
        self.machine.servos["servo1"].go_to_position(0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # go to max position
        self.net_cpu.expected_commands = {
                "XO:03,FF": "XO:P"
        }
        self.machine.servos["servo1"].go_to_position(1)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _switch_hit_cb(self, **kwargs):
        self.switch_hit = True

    def test_switches(self):
        self._test_switch_changes()
        self._test_switch_changes_nc()
        self._test_switch_configure()

    def _test_switch_configure(self):
        # last switch on first board
        self.net_cpu.expected_commands = {
            "SL:1F,01,04,04": "SL:P"
        }
        self.machine.default_platform.configure_switch('0-31', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('0-32', SwitchConfig(name="", debounce='auto', invert=0), {})

        self.net_cpu.expected_commands = {
            "SL:47,01,04,04": "SL:P"
        }
        self.machine.default_platform.configure_switch('3-15', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('4-0', SwitchConfig(name="", debounce='auto', invert=0), {})

        # last switch is 0x47. 0x48 = 72
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('72', SwitchConfig(name="", debounce='auto', invert=0), {})

    def _test_switch_changes(self):
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_flipper_eos", 1)

        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test", 0)
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("-L:07", "NET")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_test", 1)
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 1)

        self.machine.default_platform.process_received_message("/L:07", "NET")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 0)

    def _test_switch_changes_nc(self):
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test_nc", 1)
        self.assertFalse(self.switch_hit)

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 1)

        self.machine.default_platform.process_received_message("-L:1A", "NET")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 0)

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("/L:1A", "NET")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 1)
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DL:20,89,00,10,0A,FF,00,00,00": "DL:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable no hw rule
        self.net_cpu.expected_commands = {
            "DL:20,C1,00,18,0A,FF,01,00": "DL:P"
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable no hw rule
        self.net_cpu.expected_commands = {
            "TL:20,02": "TL:P"
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # flipper rule enable
        self.net_cpu.expected_commands = {
            "DL:20,01,01,18,0B,FF,01,00,00": "DL:P",
            "SL:01,01,02,02": "SL:P"
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action
        self.net_cpu.expected_commands = {
            "DL:20,89,00,10,0A,FF,00,00,00": "DL:P",    # configure and pulse
            "DL:20,01,01,18,0B,FF,01,00,00": "DL:P",    # restore rule
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action without reconfigure (same pulse)
        self.net_cpu.expected_commands = {
            "TL:20,01": "TL:P",                         # pulse
        }
        self.machine.coils["c_flipper_main"].pulse(11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (same pulse)
        self.net_cpu.expected_commands = {
            "TL:20,03": "TL:P"
        }
        self.machine.coils["c_flipper_main"].enable(pulse_ms=11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TL:20,02": "TL:P",
            "TL:20,00": "TL:P"   # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (different pulse)
        self.net_cpu.expected_commands = {
            "DL:20,C1,00,18,0A,FF,01,00": "DL:P",       # configure pwm + enable
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TL:20,02": "TL:P",
            "DL:20,01,01,18,0B,FF,01,00,00": "DN_P",    # configure rules
            "TL:20,00": "TL:P"                          # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # disable rule
        self.net_cpu.expected_commands = {
            "DL:20,81": "DL:P"
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DL:20,89,00,10,0A,FF,00,00,00": "DL:P"
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip again with cached config
        self.net_cpu.expected_commands = {
            "TL:20,01": "TL:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.net_cpu.expected_commands = {
            "DL:20,01,01,18,0A,FF,00,00,00": "DL:P",
            "DL:21,01,01,18,0A,FF,01,00,00": "DL:P",
            "SL:01,01,02,02": "SL:P",
        }
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DL:20,81": "DL:P",
            "DL:21,81": "DL:P"
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    # def test_dmd_update(self):

    #     # test configure
    #     dmd = self.machine.default_platform.configure_dmd()

    #     # test set frame to buffer
    #     frame = bytearray()
    #     for i in range(4096):
    #         frame.append(64 + i % 192)

    #     frame = bytes(frame)

    #     # test draw
    #     self.dmd_cpu.expected_commands = {
    #         b'BM:' + frame: False
    #     }
    #     dmd.update(frame)

    #     self.advance_time_and_run(.1)

    #     self.assertFalse(self.dmd_cpu.expected_commands)

    def test_bootloader_crash(self):
        # Test that the machine stops if the RGB processor sends a bootloader msg
        self.machine.stop = MagicMock()
        self.machine.default_platform.process_received_message("!B:00", "RGB")
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.stop.called)

    def test_bootloader_crash_ignored(self):
        # Test that RGB processor bootloader msgs can be ignored
        self.machine.default_platform.config['ignore_rgb_crash'] = True
        self.mock_event('fast_rgb_rebooted')
        self.machine.stop = MagicMock()
        self.machine.default_platform.process_received_message("!B:00", "RGB")
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.stop.called)
        self.assertEventCalled('fast_rgb_rebooted')

    # def test_lights_and_leds(self):
    #     self._test_matrix_light()
    #     self._test_pdb_gi_light()
    #     self._test_pdb_led()

    def _test_matrix_light(self):
        # test enable of matrix light
        self.net_cpu.expected_commands = {
            "L1:23,FF": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test enable of matrix light with brightness
        self.net_cpu.expected_commands = {
            "L1:23,80": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test disable of matrix light
        self.net_cpu.expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights["test_pdb_light"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test disable of matrix light with brightness
        self.net_cpu.expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on(brightness=255, fade_ms=100)
        self.advance_time_and_run(.02)
        self.assertFalse(self.net_cpu.expected_commands)

        # step 1
        self.net_cpu.expected_commands = {
            "L1:23,32": "L1:P",
            "L1:23,33": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.net_cpu.expected_commands))

        # step 2
        self.net_cpu.expected_commands = {
            "L1:23,65": "L1:P",
            "L1:23,66": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.net_cpu.expected_commands))

        # step 3
        self.net_cpu.expected_commands = {
            "L1:23,98": "L1:P",
            "L1:23,99": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.net_cpu.expected_commands))

        # step 4
        self.net_cpu.expected_commands = {
            "L1:23,CB": "L1:P",
            "L1:23,CC": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.net_cpu.expected_commands))

        # step 5
        self.net_cpu.expected_commands = {
            "L1:23,FE": "L1:P",
            "L1:23,FF": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.net_cpu.expected_commands))

        # step 6 if step 5 did not send FF
        if "L1:23,FE" not in self.net_cpu.expected_commands:
            self.net_cpu.expected_commands = {
                "L1:23,FF": "L1:P",
            }
            self.advance_time_and_run(.02)
            self.assertFalse(self.net_cpu.expected_commands)

    def _test_pdb_gi_light(self):
        # test gi on
        test_gi = self.machine.lights["test_gi"]
        self.net_cpu.expected_commands = {
            "GI:2A,FF": "GI:P",
        }
        test_gi.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,80": "GI:P",
        }
        test_gi.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        test_gi.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test gi off
        self.net_cpu.expected_commands = {
            "GI:2A,00": "GI:P",
        }
        test_gi.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        test_gi.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,00": "GI:P",
        }
        test_gi.on(brightness=0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_pdb_led(self):
        self.advance_time_and_run()
        test_led1 = self.machine.lights["test_led"]
        test_led2 = self.machine.lights["test_led2"]
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['98'])
        # test led on
        test_led1.on()
        self.advance_time_and_run(1)
        self.assertEqual("FFFFFF", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['98'])

        test_led2.color("001122")

        # test led off
        test_led1.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("110022", self.rgb_cpu.leds['98'])  #GRB so hardware colors need to be swapped also

        # test led color
        test_led1.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("17022A", self.rgb_cpu.leds['97'])  # GRB

        # test led off
        test_led1.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])

        self.advance_time_and_run(.02)

        # fade led over 100ms
        test_led1.color(RGBColor((100, 100, 100)), fade_ms=100)
        self.advance_time_and_run(.03)
        self.assertTrue(10 < int(self.rgb_cpu.leds['97'][0:2], 16) < 40)
        self.assertTrue(self.rgb_cpu.leds['97'][0:2] == self.rgb_cpu.leds['97'][2:4] == self.rgb_cpu.leds['97'][4:6])
        self.advance_time_and_run(.03)
        self.assertTrue(40 < int(self.rgb_cpu.leds['97'][0:2], 16) < 60)
        self.assertTrue(self.rgb_cpu.leds['97'][0:2] == self.rgb_cpu.leds['97'][2:4] == self.rgb_cpu.leds['97'][4:6])
        self.advance_time_and_run(.03)
        self.assertTrue(60 < int(self.rgb_cpu.leds['97'][0:2], 16) < 90)
        self.assertTrue(self.rgb_cpu.leds['97'][0:2] == self.rgb_cpu.leds['97'][2:4] == self.rgb_cpu.leds['97'][4:6])
        self.advance_time_and_run(2)
        self.assertEqual("646464", self.rgb_cpu.leds['97'])

    # @expect_startup_error()
    # @test_config("error_lights.yaml")
    # def test_light_errors(self):
    #     self.assertIsInstance(self.startup_error, ConfigFileError)
    #     self.assertEqual(7, self.startup_error.get_error_no())
    #     self.assertEqual("light.test_led", self.startup_error.get_logger_name())
    #     self.assertIsInstance(self.startup_error.__cause__, ConfigFileError)
    #     self.assertEqual(9, self.startup_error.__cause__.get_error_no())
    #     self.assertEqual("FAST", self.startup_error.__cause__.get_logger_name())
    #     self.assertEqual("Light syntax is number-channel (but was \"3\") for light test_led.",
    #                      self.startup_error.__cause__._message)
