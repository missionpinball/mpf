from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock

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
        msg = (self.queue.pop() + '\r').encode()
        return msg

    def read_ready(self):
        return bool(len(self.queue) > 0)

    def write_ready(self):
        return True

    def _parse(self, msg):
        return False

    def write(self, msg):
        msg_len = len(msg)
        cmd = msg.decode()
        # strip newline
        cmd = cmd[:-1]

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
            raise Exception(self.type + ": " + str(cmd))

    def stop(self):
        pass


class MockFastDmd(BaseMockFast):
    def __init__(self):
        super().__init__()
        self.type = "DMD"

    def write(self, msg):
        msg_len = len(msg)
        if msg == (b' ' * 256 * 4) + b"\r":
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


class TestFast(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/fast/'

    def get_platform(self):
        return False

    def _mock_loop(self):
        self.clock.mock_serial("com4", self.net_cpu)
        self.clock.mock_serial("com5", self.rgb_cpu)
        self.clock.mock_serial("com6", self.dmd_cpu)

    def tearDown(self):
        self.dmd_cpu.expected_commands = {
            b'BL:AA55\r': "!SRE"
        }
        self.rgb_cpu.expected_commands = {
            "BL:AA55": "!SRE"
        }
        self.net_cpu.expected_commands = {
            "WD:1": "WD:P"
        }
        super().tearDown()
        self.assertFalse(self.net_cpu.expected_commands)
        self.assertFalse(self.rgb_cpu.expected_commands)
        self.assertFalse(self.dmd_cpu.expected_commands)

    def setUp(self):
        self.expected_duration = 2
        self.net_cpu = MockFastNet()
        self.rgb_cpu = MockFastRgb()
        self.dmd_cpu = MockFastDmd()

        self.dmd_cpu.expected_commands = {
            b'ID:\r': 'ID:DMD FP-CPU-002-1 00.88',

        }
        self.rgb_cpu.expected_commands = {
            'ID:': 'ID:RGB FP-CPU-002-1 00.89',
            "RF:0": "RF:P",
            "RA:000000": "RA:P",
            "RF:00": "RF:P",
        }
        self.net_cpu.expected_commands = {
            'BR:': 'ä!B:02',
            'ID:': 'ID:NET FP-CPU-002-1 01.03',
            'NN:00': 'NN:00,FP-I/O-3208-2   ,01.00,08,20,04,06,00,00,00,00',     # 3208 board
            'NN:01': 'NN:01,FP-I/O-0804-1   ,01.00,04,08,04,06,00,00,00,00',     # 0804 board
            'NN:02': 'NN:02,FP-I/O-1616-2   ,01.00,10,10,04,06,00,00,00,00',     # 1616 board
            'NN:03': 'NN:03,FP-I/O-1616-2   ,01.00,10,10,04,06,00,00,00,00',     # 1616 board
            'NN:04': 'NN:04,,,,,,,,,,',     # no board
            "SA:": "SA:01,00,09,050000000000000000",
            "SN:01,01,04,04": "SN:P",
            "SN:02,01,04,04": "SN:P",
            "SN:03,01,04,04": "SN:P",
            "SN:16,01,04,04": "SN:P",
            "SN:07,01,1A,05": "SN:P",
            "SN:1A,01,04,04": "SN:P",
            "SN:39,01,04,04": "SN:P",
            "DN:04,00,00,00": "DN:P",
            "DN:06,00,00,00": "DN:P",
            "DN:07,00,00,00": "DN:P",
            "DN:11,00,00,00": "DN:P",
            "DN:12,00,00,00": "DN:P",
            "DN:20,00,00,00": "DN:P",
            "DN:21,00,00,00": "DN:P",
            "XO:03,7F": "XO:P",
            "XO:14,7F": "XO:P"
        }

        super().setUp()
        self.assertFalse(self.net_cpu.expected_commands)
        self.assertFalse(self.rgb_cpu.expected_commands)
        self.assertFalse(self.dmd_cpu.expected_commands)

        # test io board detection
        self.assertEqual(4, len(self.machine.default_platform.io_boards))
        self.assertEqual(32, self.machine.default_platform.io_boards[0].switch_count)
        self.assertEqual(8, self.machine.default_platform.io_boards[0].driver_count)
        self.assertEqual(8, self.machine.default_platform.io_boards[1].switch_count)
        self.assertEqual(4, self.machine.default_platform.io_boards[1].driver_count)
        self.assertEqual(16, self.machine.default_platform.io_boards[2].switch_count)
        self.assertEqual(16, self.machine.default_platform.io_boards[2].driver_count)
        self.assertEqual(16, self.machine.default_platform.io_boards[3].switch_count)
        self.assertEqual(16, self.machine.default_platform.io_boards[3].driver_count)

        self.assertEqual("00.88", self.machine.get_machine_var("fast_dmd_firmware"))
        self.assertEqual("FP-CPU-002-1", self.machine.get_machine_var("fast_dmd_model"))
        self.assertEqual("00.89", self.machine.get_machine_var("fast_rgb_firmware"))
        self.assertEqual("FP-CPU-002-1", self.machine.get_machine_var("fast_rgb_model"))
        self.assertEqual("01.03", self.machine.get_machine_var("fast_net_firmware"))
        self.assertEqual("FP-CPU-002-1", self.machine.get_machine_var("fast_net_model"))

    def test_coils(self):
        self._test_pulse()
        self._test_long_pulse()
        self._test_enable_exception()
        self._test_allow_enable()
        self._test_coil_configure()

        # test hardware scan
        info_str = """NET CPU: NET FP-CPU-002-1 01.03
RGB CPU: RGB FP-CPU-002-1 00.89
DMD CPU: DMD FP-CPU-002-1 00.88

Boards:
Board 0 - Model: FP-I/O-3208-2    Firmware: 01.00 Switches: 32 Drivers: 8
Board 1 - Model: FP-I/O-0804-1    Firmware: 01.00 Switches: 8 Drivers: 4
Board 2 - Model: FP-I/O-1616-2    Firmware: 01.00 Switches: 16 Drivers: 16
Board 3 - Model: FP-I/O-1616-2    Firmware: 01.00 Switches: 16 Drivers: 16
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_coil_configure(self):
        self.assertEqual("FAST Board 0", self.machine.coils.c_test.hw_driver.get_board_name())
        self.assertEqual("FAST Board 3", self.machine.coils.c_flipper_hold.hw_driver.get_board_name())
        # last driver on board
        self.net_cpu.expected_commands = {
            "DN:2B,00,00,00": "DN:P"
        }
        coil = self.machine.default_platform.configure_driver(self.machine.coils.c_test.hw_driver.config, '3-15',
                                                              {"connection": "network", "recycle_ms": 10})
        self.assertEqual('2B', coil.number)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # board 0 has 8 drivers. configuring driver 9 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils.c_test.hw_driver.config, '0-8',
                                                           {"connection": "network", "recycle_ms": 10})

        # only boards 0-3 exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils.c_test.hw_driver.config, '4-0',
                                                           {"connection": "network", "recycle_ms": 10})

        # only 8 + 4 + 16 + 16 = 44 = 0x2C driver exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils.c_test.hw_driver.config, '44',
                                                           {"connection": "network", "recycle_ms": 10})

    def _test_pulse(self):
        self.net_cpu.expected_commands = {
            "DN:04,81,00,10,17,FF,00,00,00": "DN:P",
            "TN:04,01": "TN:P"
        }
        # pulse coil 4
        self.machine.coils.c_test.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_long_pulse(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DN:12,C1,00,18,00,FF,FF,00": "DN:P"
        }
        self.machine.coils.c_long_pulse.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # disable command
        self.net_cpu.expected_commands = {
            "TN:12,02": "TN:P"
        }

        self.advance_time_and_run(1)
        # pulse_ms is 2000ms, so after 1s, this should not be sent
        self.assertTrue(self.net_cpu.expected_commands)

        self.advance_time_and_run(1)
        # but after 2s, it should be
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()
            self.advance_time_and_run(.1)

    def _test_allow_enable(self):
        self.net_cpu.expected_commands = {
            "DN:06,C1,00,18,17,FF,FF,00": "DN:P"
        }
        self.machine.coils.c_test_allow_enable.enable()
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
            "DN:21,01,07,10,0A,FF,00,00,14": "DN:P"
        }
        # coil and switch are on different boards but first 8 switches always work
        self.machine.autofires.ac_different_boards.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # switch and coil on board 3. should work
        self.net_cpu.expected_commands = {
            "DN:21,01,39,10,0A,FF,00,00,14": "DN:P",
            "SN:39,01,02,02": "SN:P"
        }
        self.machine.autofires.ac_board_3.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:10,01,03,10,0A,89,00,00,14": "DN:P",
        }
        # coil and switch are on different boards
        with self.assertRaises(AssertionError):
            self.machine.autofires.ac_broken_combination.enable()
            self.advance_time_and_run(.1)

    def _test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.flippers.f_test_single.config['main_coil_overwrite']['hold_power'] = 1.0
            self.machine.flippers.f_test_single.enable()

        self.machine.flippers.f_test_single.config['main_coil_overwrite']['hold_power'] = None

    def _test_two_rules_one_switch(self):
        self.net_cpu.expected_commands = {
            "SN:03,01,02,02": "SN:P",
            "DN:04,01,03,10,17,FF,00,00,1B": "DN:P",
            "DN:06,01,03,10,17,FF,00,00,2E": "DN:P"
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse(self):
        self.net_cpu.expected_commands = {
            "DN:07,01,16,10,0A,FF,00,00,14": "DN:P",  # hw rule
            "SN:16,01,02,02": "SN:P"                  # debounce quick on switch
        }
        self.machine.autofires.ac_slingshot_test.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:07,81": "DN:P"
        }
        self.machine.autofires.ac_slingshot_test.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_pwm32(self):
        self.net_cpu.expected_commands = {
            "DN:11,81,00,10,0A,AAAAAAAA,00,00,00": "DN:P",
            "TN:11,01": "TN:P"
        }
        self.machine.coils.c_pulse_pwm32_mask.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:11,C1,00,18,0A,AAAAAAAA,4A4A4A4A,00": "DN:P"
        }
        self.machine.coils.c_pulse_pwm32_mask.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.net_cpu.expected_commands = {
            "DN:07,11,1A,10,0A,FF,00,00,14": "DN:P",
            "SN:1A,01,02,02": "SN:P"
        }
        self.machine.autofires.ac_inverted_switch.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_firmware_update(self):
        commands = []

        def _catch_update(cmd):
            commands.append(cmd)
            return True
        parse_func = self.net_cpu._parse
        self.net_cpu._parse = _catch_update
        output = self.machine.default_platform.update_firmware()
        self.advance_time_and_run()
        self.net_cpu._parse = parse_func
        # check if we send the dummy update
        self.assertEqual(['BL:AA55\r>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
                          '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
                          '>>>>>>>>>>>>>>>>>>>>>>>>>\rBL:AA55\r<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'
                          '<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'
                          '<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\rBL:AA55\r>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
                          '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
                          '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\rDUMMY UPDAT'
                          'E'], commands)
        expected_output = """NET CPU is version 01.03
Found an update to version 1.04 for the NET CPU. Will flash file firmware/FAST_NET_01_04_00.txt
Update done.
"""
        self.assertEqual(expected_output, output)

    def test_servo(self):
        # go to min position
        self.net_cpu.expected_commands = {
                "XO:03,00": "XO:P"
        }
        self.machine.servos.servo1.go_to_position(0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # go to max position
        self.net_cpu.expected_commands = {
                "XO:03,FF": "XO:P"
        }
        self.machine.servos.servo1.go_to_position(1)
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
            "SN:1F,01,04,04": "SN:P"
        }
        self.machine.default_platform.configure_switch('0-31', SwitchConfig(debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('0-32', SwitchConfig(debounce='auto', invert=0), {})

        self.net_cpu.expected_commands = {
            "SN:47,01,04,04": "SN:P"
        }
        self.machine.default_platform.configure_switch('3-15', SwitchConfig(debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('4-0', SwitchConfig(debounce='auto', invert=0), {})

        # last switch is 0x47. 0x48 = 72
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('72', SwitchConfig(debounce='auto', invert=0), {})

    def _test_switch_changes(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_flipper"))
        self.assertTrue(self.machine.switch_controller.is_active("s_flipper_eos"))

        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("-N:07", "NET")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        self.machine.default_platform.process_received_message("/N:07", "NET")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))

    def _test_switch_changes_nc(self):
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertFalse(self.switch_hit)

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))

        self.machine.default_platform.process_received_message("-N:1A", "NET")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_nc"))

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("/N:1A", "NET")
        self.advance_time_and_run(1)

        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,81,00,10,0A,FF,00,00,00": "DN:P",
            "TN:20,01": "TN:P",
        }
        self.machine.coils.c_flipper_main.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00": "DN:P"
        }
        self.machine.coils.c_flipper_main.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable no hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P"
        }
        self.machine.coils.c_flipper_main.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # flipper rule enable
        self.net_cpu.expected_commands = {
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",
            "SN:01,01,02,02": "SN:P"
        }
        self.machine.flippers.f_test_single.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action
        self.net_cpu.expected_commands = {
            "DN:20,81,00,10,0A,FF,00,00,00": "DN:P",    # configure pulse
            "TN:20,01": "TN:P",                         # pulse
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",    # restore rule
        }
        self.machine.coils.c_flipper_main.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action without reconfigure (same pulse)
        self.net_cpu.expected_commands = {
            "TN:20,01": "TN:P",                         # pulse
        }
        self.machine.coils.c_flipper_main.pulse(11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (same pulse)
        self.net_cpu.expected_commands = {
            "TN:20,03": "TN:P"
        }
        self.machine.coils.c_flipper_main.enable(pulse_ms=11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P",
            "TN:20,00": "TN:P"   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (different pulse)
        self.net_cpu.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00": "DN:P",       # configure pwm + enable
        }
        self.machine.coils.c_flipper_main.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P",
            "DN:20,01,01,18,0B,FF,01,00,00": "DN_P",    # configure rules
            "TN:20,00": "TN:P"                          # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # disable rule
        self.net_cpu.expected_commands = {
            "DN:20,81": "DN:P"
        }
        self.machine.flippers.f_test_single.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,81,00,10,0A,FF,00,00,00": "DN:P",
            "TN:20,01": "TN:P",
        }
        self.machine.coils.c_flipper_main.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip again with cached config
        self.net_cpu.expected_commands = {
            "TN:20,01": "TN:P",
        }
        self.machine.coils.c_flipper_main.pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.net_cpu.expected_commands = {
            "DN:20,01,01,18,0A,FF,00,00,00": "DN:P",
            "DN:21,01,01,18,0A,FF,01,00,00": "DN:P",
            "SN:01,01,02,02": "SN:P",
        }
        self.machine.flippers.f_test_hold.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:20,81": "DN:P",
            "DN:21,81": "DN:P"
        }
        self.machine.flippers.f_test_hold.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_dmd_update(self):

        # test configure
        dmd = self.machine.default_platform.configure_dmd()

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(i % 256)

        frame = bytes(frame)

        # test draw
        self.dmd_cpu.expected_commands = {
            b'BM:' + frame: False
        }
        dmd.update(frame)

        self.advance_time_and_run(.1)

        self.assertFalse(self.dmd_cpu.expected_commands)

    def test_lights_and_leds(self):
        self._test_matrix_light()
        self._test_pdb_gi_light()
        self._test_pdb_led()

    def _test_matrix_light(self):
        # test enable of matrix light
        self.net_cpu.expected_commands = {
            "L1:23,FF": "L1:P",
        }
        self.machine.lights.test_pdb_light.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test enable of matrix light with brightness
        self.net_cpu.expected_commands = {
            "L1:23,80": "L1:P",
        }
        self.machine.lights.test_pdb_light.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test disable of matrix light
        self.net_cpu.expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights.test_pdb_light.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test disable of matrix light with brightness
        self.net_cpu.expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights.test_pdb_light.on(brightness=255, fade_ms=100)
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
        device = self.machine.lights.test_gi
        self.net_cpu.expected_commands = {
            "GI:2A,FF": "GI:P",
        }
        device.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,80": "GI:P",
        }
        device.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        device.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test gi off
        self.net_cpu.expected_commands = {
            "GI:2A,00": "GI:P",
        }
        device.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,00": "GI:P",
        }
        device.on(brightness=0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_pdb_led(self):
        self.advance_time_and_run()
        device = self.machine.lights.test_led
        device2 = self.machine.lights.test_led2
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['99'])
        # test led on
        device.on()
        self.advance_time_and_run(1)
        self.assertEqual("ffffff", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['99'])

        device2.color("001122")

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("001122", self.rgb_cpu.leds['99'])

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("02172a", self.rgb_cpu.leds['97'])
