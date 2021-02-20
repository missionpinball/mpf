from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.platforms.pkone.pkone_coil import PKONECoilNumber
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock

from mpf.tests.loop import MockSerial


class BaseMockPKONE(MockSerial):

    def __init__(self):
        super().__init__()
        self.queue = []
        self.expected_commands = {}
        self.ignore_commands = {}

    def read(self, length):
        del length
        if not self.queue:
            return
        msg = (self.queue.pop() + 'E').encode('ascii', 'replace')
        return msg

    def read_ready(self):
        return bool(len(self.queue) > 0)

    def write_ready(self):
        return True

    def _parse(self, msg):
        return False

    def write(self, msg):
        parts = msg.split(b'E')
        # remove last newline
        assert parts.pop() == b''

        for part in parts:
            self._handle_msg(part)

        return len(msg)

    def _handle_msg(self, msg):
        msg_len = len(msg)
        cmd = msg.decode()
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
            raise Exception(str(cmd))

    def stop(self):
        pass


class TestPKONE(MpfTestCase):
    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/pkone/'

    def get_platform(self):
        return False

    def _mock_loop(self):
        self.clock.mock_serial("com3", self.controller)

    def tearDown(self):
        self.controller.expected_commands = {
            'PRS': 'PRS',
        }
        super().tearDown()
        self.assertFalse(self.controller.expected_commands)

    def setUp(self):
        self.expected_duration = 2
        self.controller = BaseMockPKONE()

        self.controller.expected_commands = {
            'PCN': 'PCNF11H1',
            'PCB0': 'PCB0XF11H2PY',
            'PCB1': 'PCB1XF11H2PN',
            'PCB2': 'PCB2LF10H1',
            'PCB3': 'PCB3N',
            'PCB4': 'PCB4N',
            'PCB5': 'PCB5N',
            'PCB6': 'PCB6N',
            'PCB7': 'PCB7N',
            'PRS': 'PRS',
            'PSA': 'PSA011000000000000000000000000000000000X100000000000000000000000000000000000XE',
            'PCC0040000000000': None,
            'PCC0060000000000': None,
            'PCC0070000000000': None,
            'PCC1080000000000': None,
            'PCC1010000000000': None,
            'PCC1020000000000': None,
        }

        super().setUp()
        self.advance_time_and_run()
        self.assertFalse(self.controller.expected_commands)

        # test add-on board detection
        self.assertEqual(2, len(self.machine.default_platform.pkone_extensions))
        self.assertEqual(35, self.machine.default_platform.pkone_extensions[0].switch_count)
        self.assertEqual(10, self.machine.default_platform.pkone_extensions[0].coil_count)
        self.assertEqual(4, self.machine.default_platform.pkone_extensions[0].servo_count)
        self.assertEqual(0, self.machine.default_platform.pkone_extensions[0].addr)
        self.assertEqual(35, self.machine.default_platform.pkone_extensions[1].switch_count)
        self.assertEqual(10, self.machine.default_platform.pkone_extensions[1].coil_count)
        self.assertEqual(4, self.machine.default_platform.pkone_extensions[1].servo_count)
        self.assertEqual(1, self.machine.default_platform.pkone_extensions[1].addr)

        self.assertEqual(1, len(self.machine.default_platform.pkone_lightshows))
        self.assertEqual(45, self.machine.default_platform.pkone_lightshows[2].simple_led_count)
        self.assertEqual(8, self.machine.default_platform.pkone_lightshows[2].led_groups)
        self.assertEqual(64, self.machine.default_platform.pkone_lightshows[2].max_leds_per_group)
        self.assertEqual(2, self.machine.default_platform.pkone_lightshows[2].addr)

        self.assertEqual("1.1", self.machine.variables.get_machine_var("pkone_firmware"))
        self.assertEqual("PKONE Nano Controller (rev 1)", self.machine.variables.get_machine_var("pkone_hardware"))

    def test_coils(self):
        self._test_pulse()
        self._test_long_pulse()
        self._test_enable_exception()
        self._test_allow_enable()
        self._test_coil_configure()

        # test hardware scan
        info_str = """Penny K Pinball Hardware
------------------------
 - Connected Controllers:
   -> PKONE Nano - Port: com3 at 115200 baud (firmware v1.1, hardware rev 1).

 - Extension boards:
   -> Address ID: 0 (firmware v1.1, hardware rev 2)
   -> Address ID: 1 (firmware v1.1, hardware rev 2)

 - Lightshow boards:
   -> Address ID: 2 (firmware v1.0, hardware rev 1)
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_coil_configure(self):
        self.assertEqual("PKONE Extension Board 0", self.machine.coils["c_test"].hw_driver.get_board_name())
        self.assertEqual("PKONE Extension Board 1", self.machine.coils["c_flipper_hold"].hw_driver.get_board_name())
        # last driver on board
        self.controller.expected_commands = {
            "PCC1100000000000": None
        }
        coil = self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '1-10',
                                                              {"recycle_ms": 10})
        self.assertEqual(PKONECoilNumber(1, 10), coil.number)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # board 0 has 10 coils/drivers. configuring driver 17 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '0-17',
                                                           {"recycle_ms": 10})

        # board 0 has 10 coils/drivers. configuring driver 11 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '0-11',
                                                           {"recycle_ms": 10})

        # board 0 has 10 coils/drivers. configuring driver 0 should not work (only 1-10)
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '0-0',
                                                           {"recycle_ms": 10})

        # only extension boards 0-1 exist
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '4-1',
                                                           {"recycle_ms": 10})

        # a lightshow board is at address id 2 (no coils are on a lightshow board)
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '2-1',
                                                           {"recycle_ms": 10})

    def _test_pulse(self):
        self.controller.expected_commands = {
            "PCC0040239900027": None,
            "PCP004": None
        }
        # pulse coil 4f
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_long_pulse(self):
        # enable command
        self.controller.expected_commands = {
            "PCC1080009999000": None,
            "PCH108": None
        }
        self.machine.coils["c_long_pulse"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # disable command
        self.controller.expected_commands = {
            "PCR108": None
        }

        self.advance_time_and_run(1)
        # pulse_ms is 2000ms, so after 1s, this should not be sent
        self.assertTrue(self.controller.expected_commands)

        self.advance_time_and_run(1)
        # but after 2s, it should be
        self.assertFalse(self.controller.expected_commands)

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils["c_test"].enable()
            self.advance_time_and_run(.1)

    def _test_allow_enable(self):
        self.controller.expected_commands = {
            "PCC0060239999000": None,
            "PCH006": None
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_rules(self):
        self._test_enable_exception_hw_rule()
        self._test_two_rules_one_switch()
        self._test_hw_rule_pulse()
        self._test_hw_rule_pulse_inverted_switch()
        self._test_hw_rule_same_board()

    def _test_hw_rule_same_board(self):
        # coil and switch are on different boards
        with self.assertRaises(AssertionError):
            self.machine.autofires["ac_different_boards"].enable()
            self.advance_time_and_run(.1)

        # switch and coil on board with address id 1. should work
        self.controller.expected_commands = {
            "PHR10210100000000109900000": None
        }
        self.machine.autofires["ac_board_3"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.flippers["f_test_single"].config['main_coil_overwrite']['hold_power'] = 1.0
            self.machine.flippers["f_test_single"].enable()

        self.machine.flippers["f_test_single"].config['main_coil_overwrite']['hold_power'] = None

    def _test_two_rules_one_switch(self):
        self.controller.expected_commands = {
            "PHR00410300000000239900027": None,
            "PHR00610300000000239900000": None
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_hw_rule_pulse(self):
        self.controller.expected_commands = {
            "PHR00712200000000109900000": None     # hw rule
        }
        self.machine.autofires["ac_slingshot_test"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "PHD007": None
        }
        self.machine.autofires["ac_slingshot_test"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.controller.expected_commands = {
            "PHR00712610000000109900000": None
        }
        self.machine.autofires["ac_inverted_switch"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_servo(self):
        # go to min position
        self.controller.expected_commands = {
                "XO:03,00": "XO:P"
        }
        self.machine.servos["servo1"].go_to_position(0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # go to max position
        self.controller.expected_commands = {
                "XO:03,FF": "XO:P"
        }
        self.machine.servos["servo1"].go_to_position(1)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _switch_hit_cb(self, **kwargs):
        self.switch_hit = True

    def test_switches(self):
        self._test_switch_changes()
        self._test_switch_changes_nc()
        self._test_switch_configure()

    def _test_switch_configure(self):
        # last switch on first board
        self.controller.expected_commands = {
            "SN:1F,01,04,04": "SN:P"
        }
        self.machine.default_platform.configure_switch('0-31', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('0-32', SwitchConfig(name="", debounce='auto', invert=0), {})

        self.controller.expected_commands = {
            "SN:47,01,04,04": "SN:P"
        }
        self.machine.default_platform.configure_switch('3-15', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

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
        self.machine.default_platform.process_received_message("-N:07", "NET")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_test", 1)
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 1)

        self.machine.default_platform.process_received_message("/N:07", "NET")
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

        self.machine.default_platform.process_received_message("-N:1A", "NET")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 0)

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("/N:1A", "NET")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 1)
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.controller.expected_commands = {
            "DN:20,81,00,10,0A,FF,00,00,00": "DN:P",
            "TN:20,01": "TN:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual enable no hw rule
        self.controller.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00": "DN:P"
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual disable no hw rule
        self.controller.expected_commands = {
            "TN:20,02": "TN:P"
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # flipper rule enable
        self.controller.expected_commands = {
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",
            "SN:01,01,02,02": "SN:P"
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip with hw rule in action
        self.controller.expected_commands = {
            "DN:20,81,00,10,0A,FF,00,00,00": "DN:P",    # configure pulse
            "TN:20,01": "TN:P",                         # pulse
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",    # restore rule
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip with hw rule in action without reconfigure (same pulse)
        self.controller.expected_commands = {
            "TN:20,01": "TN:P",                         # pulse
        }
        self.machine.coils["c_flipper_main"].pulse(11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual enable with hw rule (same pulse)
        self.controller.expected_commands = {
            "TN:20,03": "TN:P"
        }
        self.machine.coils["c_flipper_main"].enable(pulse_ms=11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual disable with hw rule
        self.controller.expected_commands = {
            "TN:20,02": "TN:P",
            "TN:20,00": "TN:P"   # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual enable with hw rule (different pulse)
        self.controller.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00": "DN:P",       # configure pwm + enable
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual disable with hw rule
        self.controller.expected_commands = {
            "TN:20,02": "TN:P",
            "DN:20,01,01,18,0B,FF,01,00,00": "DN_P",    # configure rules
            "TN:20,00": "TN:P"                          # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # disable rule
        self.controller.expected_commands = {
            "DN:20,81": "DN:P"
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip no hw rule
        self.controller.expected_commands = {
            "DN:20,81,00,10,0A,FF,00,00,00": "DN:P",
            "TN:20,01": "TN:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip again with cached config
        self.controller.expected_commands = {
            "TN:20,01": "TN:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.controller.expected_commands = {
            "DN:20,01,01,18,0A,FF,00,00,00": "DN:P",
            "DN:21,01,01,18,0A,FF,01,00,00": "DN:P",
            "SN:01,01,02,02": "SN:P",
        }
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "DN:20,81": "DN:P",
            "DN:21,81": "DN:P"
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_dmd_update(self):

        # test configure
        dmd = self.machine.default_platform.configure_dmd()

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(64 + i % 192)

        frame = bytes(frame)

        # test draw
        self.dmd_cpu.expected_commands = {
            b'BM:' + frame: False
        }
        dmd.update(frame)

        self.advance_time_and_run(.1)

        self.assertFalse(self.dmd_cpu.expected_commands)

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

    def test_lights_and_leds(self):
        self._test_matrix_light()
        self._test_pdb_gi_light()
        self._test_pdb_led()

    def _test_matrix_light(self):
        # test enable of matrix light
        self.controller.expected_commands = {
            "L1:23,FF": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test enable of matrix light with brightness
        self.controller.expected_commands = {
            "L1:23,80": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test disable of matrix light
        self.controller.expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights["test_pdb_light"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test disable of matrix light with brightness
        self.controller.expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on(brightness=255, fade_ms=100)
        self.advance_time_and_run(.02)
        self.assertFalse(self.controller.expected_commands)

        # step 1
        self.controller.expected_commands = {
            "L1:23,32": "L1:P",
            "L1:23,33": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.controller.expected_commands))

        # step 2
        self.controller.expected_commands = {
            "L1:23,65": "L1:P",
            "L1:23,66": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.controller.expected_commands))

        # step 3
        self.controller.expected_commands = {
            "L1:23,98": "L1:P",
            "L1:23,99": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.controller.expected_commands))

        # step 4
        self.controller.expected_commands = {
            "L1:23,CB": "L1:P",
            "L1:23,CC": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.controller.expected_commands))

        # step 5
        self.controller.expected_commands = {
            "L1:23,FE": "L1:P",
            "L1:23,FF": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.controller.expected_commands))

        # step 6 if step 5 did not send FF
        if "L1:23,FE" not in self.controller.expected_commands:
            self.controller.expected_commands = {
                "L1:23,FF": "L1:P",
            }
            self.advance_time_and_run(.02)
            self.assertFalse(self.controller.expected_commands)

    def _test_pdb_gi_light(self):
        # test gi on
        device = self.machine.lights["test_gi"]
        self.controller.expected_commands = {
            "GI:2A,FF": "GI:P",
        }
        device.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "GI:2A,80": "GI:P",
        }
        device.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        device.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test gi off
        self.controller.expected_commands = {
            "GI:2A,00": "GI:P",
        }
        device.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        device.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "GI:2A,00": "GI:P",
        }
        device.on(brightness=0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_pdb_led(self):
        self.advance_time_and_run()
        device = self.machine.lights["test_led"]
        device2 = self.machine.lights["test_led2"]
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['98'])
        # test led on
        device.on()
        self.advance_time_and_run(1)
        self.assertEqual("ffffff", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['98'])

        device2.color("001122")

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("001122", self.rgb_cpu.leds['98'])

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("02172a", self.rgb_cpu.leds['97'])
