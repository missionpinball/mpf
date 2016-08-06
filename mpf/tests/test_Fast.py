from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase

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
        msg = (self.queue.pop() + '\r').encode()
        return msg

    def read_ready(self):
        return bool(len(self.queue) > 0)

    def write_ready(self):
        return False

    def _parse(self, msg):
        return False

    def write(self, msg):
        msg_len = len(msg)
        cmd = msg.decode()
        # strip newline
        cmd = cmd[:-1]

        # ignore init garbage
        if cmd == (' ' * 256):
            return msg_len

        if cmd[:3] == "WD:":
            return msg_len

        if cmd in self.ignore_commands:
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
        if msg == (b' ' * 256) + b"\r":
            return msg_len

        cmd = msg

        if cmd[:3] == "WD:":
            return msg_len

        if cmd in self.ignore_commands:
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
            self.leds[cmd[3:5]] = cmd[5:]
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
        return 'fast'

    def _mock_loop(self):
        self.clock.mock_serial("com4", self.net_cpu)
        self.clock.mock_serial("com5", self.rgb_cpu)
        self.clock.mock_serial("com6", self.dmd_cpu)

    def setUp(self):
        self.net_cpu = MockFastNet()
        self.rgb_cpu = MockFastRgb()
        self.dmd_cpu = MockFastDmd()

        self.dmd_cpu.expected_commands = {
            b'ID:\r': 'ID:DMD FP-CPU-002-1 00.88',

        }
        self.rgb_cpu.expected_commands = {
            'ID:': 'ID:RGB FP-CPU-002-1 00.88',
            "RF:0": False,
            "RA:000000": False,
            "RF:00": False,
        }
        self.net_cpu.expected_commands = {
            'ID:': 'ID:NET FP-CPU-002-1 00.88',
            'NN:0': 'NN:00,FP-I/O-3208-2   ,01.00,08,20,04,06,00,00,00,00',     # 3208 board
            'NN:1': 'NN:01,FP-I/O-0804-1   ,01.00,04,08,04,06,00,00,00,00',     # 0804 board
            'NN:2': 'NN:02,FP-I/O-1616-2   ,01.00,10,10,04,06,00,00,00,00',     # 1616 board
            'NN:3': 'NN:03,FP-I/O-1616-2   ,01.00,10,10,04,06,00,00,00,00',     # 1616 board
            "SA:": "SA:0,00,4,05000000",
            "SN:01,01,0A,0A": "SN:P",
            "SN:02,01,0A,0A": "SN:P",
            "SN:03,01,0A,0A": "SN:P",
            "SN:16,01,0A,0A": "SN:P",
            "SN:07,01,0A,0A": "SN:P",
            "SN:1A,01,0A,0A": "SN:P",
            "DN:04,00,00,00": False,
            "DN:06,00,00,00": False,
            "DN:07,00,00,00": False,
            "DN:10,00,00,00": False,
            "DN:11,00,00,00": False,
            "DN:12,00,00,00": False,
            "DN:20,00,00,00": False,
            "DN:21,00,00,00": False,
            "GI:2A,FF": False,
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

    def test_coils(self):
        self._test_pulse()
        self._test_long_pulse()
        self._test_enable_exception()
        self._test_allow_enable()
        self._test_coil_configure()

    def _test_coil_configure(self):
        # last driver on board
        self.net_cpu.expected_commands = {
            "DN:2B,00,00,00": False
        }
        coil = self.machine.default_platform.configure_driver({'number': '3-15'})
        self.assertEqual('2B', coil.number)
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        # board 0 has 8 drivers. configuring driver 9 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver({'number': '0-8'})

        # only boards 0-3 exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver({'number': '4-0'})

        # only 8 + 4 + 16 + 16 = 44 = 0x2C driver exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver({'number': '2C'})

    def _test_pulse(self):
        self.net_cpu.expected_commands = {
            "DN:04,89,00,10,17,ff,00,00,00": False
        }
        # pulse coil 4
        self.machine.coils.c_test.pulse()
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_long_pulse(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DN:12,C1,00,18,00,ff,ff,00": False
        }
        self.machine.coils.c_long_pulse.pulse()
        self.assertFalse(self.net_cpu.expected_commands)

        # disable command
        self.net_cpu.expected_commands = {
            "TN:12,02": False
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

    def _test_allow_enable(self):
        self.net_cpu.expected_commands = {
            "DN:06,C1,00,18,17,ff,ff,00": False
        }
        self.machine.coils.c_test_allow_enable.enable()
        self.assertFalse(self.net_cpu.expected_commands)

    def test_rules(self):
        self._test_enable_exception_hw_rule()
        self._test_two_rules_one_switch()
        self._test_hw_rule_pulse()
        self._test_hw_rule_pulse_pwm()
        self._test_hw_rule_pulse_pwm32()
        self._test_hw_rule_pulse_inverted_switch()
        self._test_hw_rule_same_board()

    def _test_hw_rule_same_board(self):
        self.net_cpu.expected_commands = {
            "DN:21,01,07,10,0A,ff,00,00,14": False,
            "SN:07,01,02,02": False
        }
        # coil and switch are on different boards but first 8 switches always work
        self.machine.autofires.ac_different_boards.enable()
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:10,01,03,10,0A,89,00,00,14": False,
        }
        # coil and switch are on different boards
        with self.assertRaises(AssertionError):
            self.machine.autofires.ac_broken_combination.enable()

    def _test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule(
                self.machine.switches.s_test,
                self.machine.coils.c_test)

    def _test_two_rules_one_switch(self):
        self.net_cpu.expected_commands = {
            "SN:03,01,02,02": False,
            "DN:04,01,03,10,17,ff,00,00,2E": False,
            "DN:06,01,03,10,17,ff,00,00,2E": False
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse(self):
        self.net_cpu.expected_commands = {
            "DN:07,01,16,10,0A,ff,00,00,14": False,  # hw rule
            "SN:16,01,02,02": False                  # debounce quick on switch
        }
        self.machine.autofires.ac_slingshot_test.enable()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:07,81": False
        }
        self.machine.autofires.ac_slingshot_test.disable()
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_pwm(self):
        self.net_cpu.expected_commands = {
            "DN:10,89,00,10,0A,89,00,00,00": False
        }
        self.machine.coils.c_pulse_pwm_mask.pulse()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:10,C1,00,18,0A,89,AA,00": False
        }
        self.machine.coils.c_pulse_pwm_mask.enable()
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_pwm32(self):
        self.net_cpu.expected_commands = {
            "DN:11,89,00,10,0A,89898989,00,00,00": False
        }
        self.machine.coils.c_pulse_pwm32_mask.pulse()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:11,C1,00,18,0A,89898989,AA89AA89,00": False
        }
        self.machine.coils.c_pulse_pwm32_mask.enable()
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.net_cpu.expected_commands = {
            "DN:07,11,1A,10,0A,ff,00,00,14": False,
            "SN:1A,01,02,02": False
        }
        self.machine.autofires.ac_inverted_switch.enable()
        self.assertFalse(self.net_cpu.expected_commands)

    def test_servo(self):
        # go to min position
        self.net_cpu.expected_commands = {
                "XO:03,00": False
        }
        self.machine.servos.servo1.go_to_position(0)
        self.assertFalse(self.net_cpu.expected_commands)

        # go to max position
        self.net_cpu.expected_commands = {
                "XO:03,FF": False
        }
        self.machine.servos.servo1.go_to_position(1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _switch_hit_cb(self):
        self.switch_hit = True

    def test_switches(self):
        self._test_switch_changes()
        self._test_switch_changes_nc()
        self._test_switch_configure()

    def _test_switch_configure(self):
        # last switch on first board
        self.net_cpu.expected_commands = {
            "SN:1F,01,0A,0A": False
        }
        self.machine.default_platform.configure_switch({'number': '0-31', 'debounce': 'auto'})
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch({'number': '0-32', 'debounce': 'auto'})

        self.net_cpu.expected_commands = {
            "SN:47,01,0A,0A": False
        }
        self.machine.default_platform.configure_switch({'number': '3-15', 'debounce': 'auto'})
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch({'number': '4-0', 'debounce': 'auto'})

        # last switch is 0x47
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch({'number': '48', 'debounce': 'auto'})

    def _test_switch_changes(self):
        self.assertFalse(self.machine.switch_controller.is_active("s_flipper"))
        self.assertTrue(self.machine.switch_controller.is_active("s_flipper_eos"))

        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("-N:07")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        self.machine.default_platform.process_received_message("/N:07")
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

        self.machine.default_platform.process_received_message("-N:1A")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_nc"))

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("/N:1A")
        self.advance_time_and_run(1)

        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,89,00,10,0A,ff,00,00,00": False
        }
        self.machine.coils.c_flipper_main.pulse()
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,C1,00,18,0A,ff,01,00": False
        }
        self.machine.coils.c_flipper_main.enable()
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable no hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": False
        }
        self.machine.coils.c_flipper_main.disable()
        self.assertFalse(self.net_cpu.expected_commands)

        # enable
        self.net_cpu.expected_commands = {
            "DN:20,01,01,18,0B,ff,01,00,00": False,
            "SN:01,01,02,02": False
        }
        self.machine.flippers.f_test_single.enable()
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action
        self.net_cpu.expected_commands = {
            "TN:20,01": False,  # pulse
            "TN:20,00": False   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.pulse()
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule
        self.net_cpu.expected_commands = {
            "TN:20,03": False
        }
        self.machine.coils.c_flipper_main.enable()
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": False,
            "TN:20,00": False   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.disable()
        self.assertFalse(self.net_cpu.expected_commands)

        # disable
        self.net_cpu.expected_commands = {
            "DN:20,81": False
        }
        self.machine.flippers.f_test_single.disable()
        self.assertFalse(self.net_cpu.expected_commands)

    def test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.net_cpu.expected_commands = {
            "DN:20,01,01,18,0A,ff,00,00,00": False,
            "DN:21,01,01,18,0A,ff,01,00,00": False,
            "SN:01,01,02,02": False,
        }
        self.machine.flippers.f_test_hold.enable()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:20,81": False,
            "DN:21,81": False
        }
        self.machine.flippers.f_test_hold.disable()
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

        self.machine_run()

        self.assertFalse(self.dmd_cpu.expected_commands)

    def test_lights_and_leds(self):
        self._test_matrix_light()
        self._test_pdb_gi_light()
        self._test_rdb_led()

    def _test_matrix_light(self):
        # test enable of matrix light
        self.net_cpu.expected_commands = {
            "L1:23,FF": False,
        }
        self.machine.lights.test_pdb_light.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test enable of matrix light with brightness
        self.net_cpu.expected_commands = {
            "L1:23,80": False,
        }
        self.machine.lights.test_pdb_light.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test disable of matrix light
        self.net_cpu.expected_commands = {
            "L1:23,00": False,
        }
        self.machine.lights.test_pdb_light.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # test disable of matrix light with brightness
        self.net_cpu.expected_commands = {
            "L1:23,00": False,
        }
        self.machine.lights.test_pdb_light.on(brightness=0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_pdb_gi_light(self):
        # test gi on
        device = self.machine.gis.test_gi
        self.net_cpu.expected_commands = {
            "GI:2A,FF": False,
        }
        device.enable()
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,80": False,
        }
        device.enable(brightness=128)
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,F5": False,
        }
        device.enable(brightness=245)
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        # test gi off
        self.net_cpu.expected_commands = {
            "GI:2A,00": False,
        }
        device.disable()
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "GI:2A,00": False,
        }
        device.enable(brightness=0)
        self.machine_run()
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_rdb_led(self):
        self.advance_time_and_run()
        device = self.machine.leds.test_led
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.rgb_cpu.leds = {}
        # test led on
        device.on()
        self.advance_time_and_run(1)
        self.assertEqual("ffffff", self.rgb_cpu.leds['97'])

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("02172a", self.rgb_cpu.leds['97'])
