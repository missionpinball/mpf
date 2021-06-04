from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.platforms.pkone.pkone import PKONEHardwarePlatform
from mpf.platforms.pkone.pkone_coil import PKONECoilNumber
from mpf.platforms.pkone.pkone_servo import PKONEServoNumber
from mpf.tests.MpfTestCase import MpfTestCase

from mpf.tests.loop import MockSerial


class BaseMockPKONE(MockSerial):

    def __init__(self):
        super().__init__()
        self.queue = []
        self.expected_commands = {}
        self.ignore_commands = {}
        self.sent_commands = []
        self.validate_expected_commands_mode = True

    def reset(self):
        self.expected_commands = {}
        self.sent_commands = []
        self.validate_expected_commands_mode = True

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

        # handle watchdog message
        if cmd == "PWD":
            self.queue.append("PWD")
            return msg_len

        if cmd in self.ignore_commands:
            return msg_len

        if self._parse(cmd):
            return msg_len

        if self.validate_expected_commands_mode:
            if cmd in self.expected_commands:
                if self.expected_commands[cmd]:
                    self.queue.append(self.expected_commands[cmd])
                del self.expected_commands[cmd]
                self.sent_commands.append(cmd)
                return msg_len
            else:
                raise Exception(str(cmd))
        else:
            self.sent_commands.append(cmd)
            return msg_len

    def stop(self):
        pass


class TestPKONE(MpfTestCase):

    """Test the Penny K Pinball PKONE hardware platform."""

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
            'PCN': 'PCNF11H1',          # Nano controller (firmware 1.1, hardware rev 1)
            'PCB0': 'PCB0XF11H2PY',     # Extension board at ID 0 (firmware 1.1, hardware rev 2, high power on)
            'PCB1': 'PCB1XF11H2PN',     # Extension board at ID 1 (firmware 1.1, hardware rev 2, high power off)
            'PCB2': 'PCB2LF10H1RGB',    # Lightshow board at ID 2 (RGB firmware 1.0, hardware rev 1)
            'PCB3': 'PCB2LF10H1RGBW',   # Lightshow board at ID 3 (RGBW firmware 1.0, hardware rev 1)
            'PCB4': 'PCB4N',
            'PCB5': 'PCB5N',
            'PCB6': 'PCB6N',
            'PCB7': 'PCB7N',
            'PRS': 'PRS',
            'PWS1000': 'PWS',
            'PSA0': 'PSA011000000000000000000000000000000000E',
            'PSA1': 'PSA100110000000000000000000000000000000E',
            'PCC1040000000000': 'PCC',
            'PCC1060000000000': 'PCC',
            'PCC0070000000000': 'PCC',
            'PCC1080000000000': 'PCC',
            'PCC1010000000000': 'PCC',
            'PCC1020000000000': 'PCC',
            'PSC011003': 'PSC',
            'PSC014125': 'PSC',
            'PLB2101050000000000000000000000000000000000000000000000000': 'PLB',
            'PWB3101040000000000000000000000000000000000000000000000000000': 'PWB',
        }

        super().setUp()
        self.advance_time_and_run()
        self.assertFalse(self.controller.expected_commands)

        # test add-on board detection
        self.assertIsInstance(self.machine.default_platform, PKONEHardwarePlatform)
        self.assertEqual(2, len(self.machine.default_platform.pkone_extensions))
        self.assertEqual(35, self.machine.default_platform.pkone_extensions[0].switch_count)
        self.assertEqual(10, self.machine.default_platform.pkone_extensions[0].coil_count)
        self.assertEqual(4, self.machine.default_platform.pkone_extensions[0].servo_count)
        self.assertEqual(0, self.machine.default_platform.pkone_extensions[0].addr)

        self.assertEqual(35, self.machine.default_platform.pkone_extensions[1].switch_count)
        self.assertEqual(10, self.machine.default_platform.pkone_extensions[1].coil_count)
        self.assertEqual(4, self.machine.default_platform.pkone_extensions[1].servo_count)
        self.assertEqual(1, self.machine.default_platform.pkone_extensions[1].addr)

        self.assertEqual(2, len(self.machine.default_platform.pkone_lightshows))
        self.assertFalse(self.machine.default_platform.pkone_lightshows[2].rgbw_firmware)
        self.assertEqual(40, self.machine.default_platform.pkone_lightshows[2].simple_led_count)
        self.assertEqual(8, self.machine.default_platform.pkone_lightshows[2].led_groups)
        self.assertEqual(64, self.machine.default_platform.pkone_lightshows[2].max_leds_per_group)
        self.assertEqual(2, self.machine.default_platform.pkone_lightshows[2].addr)

        self.assertTrue(self.machine.default_platform.pkone_lightshows[3].rgbw_firmware)
        self.assertEqual(40, self.machine.default_platform.pkone_lightshows[3].simple_led_count)
        self.assertEqual(8, self.machine.default_platform.pkone_lightshows[3].led_groups)
        self.assertEqual(64, self.machine.default_platform.pkone_lightshows[3].max_leds_per_group)
        self.assertEqual(3, self.machine.default_platform.pkone_lightshows[3].addr)

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
   -> Address ID: 2 (RGB firmware v1.0, hardware rev 1)
   -> Address ID: 3 (RGBW firmware v1.0, hardware rev 1)
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_coil_configure(self):
        self.assertEqual("PKONE Extension Board 0", self.machine.coils["c_slingshot_test"].hw_driver.get_board_name())
        self.assertEqual("PKONE Extension Board 1", self.machine.coils["c_test"].hw_driver.get_board_name())
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
            "PCC1040239900027": None,
            "PCP104": None
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
            "PCC1060239999000": None,
            "PCH106": None
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
            self.machine.autofire_coils["ac_different_boards"].enable()
            self.advance_time_and_run(.1)

        # switch and coil on board with address id 1. should work
        self.controller.expected_commands = {
            "PHR10210300000000109900000": None
        }
        self.machine.autofire_coils["ac_board_3"].enable()
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
            "PHR10410700000000239900027": None,
            "PHR10610700000000239900000": None
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_hw_rule_pulse(self):
        self.controller.expected_commands = {
            "PHR00712200000000109900000": None     # hw rule
        }
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "PHD007": None
        }
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.controller.expected_commands = {
            "PHR00712610000000109900000": None
        }
        self.machine.autofire_coils["ac_inverted_switch"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_servo(self):
        # test servo numbers
        self.assertIsInstance(self.machine.default_platform, PKONEHardwarePlatform)
        servo_number = self.machine.default_platform._parse_servo_number("0-11")
        self.assertEqual(11, servo_number.servo_number)
        servo_number = self.machine.default_platform._parse_servo_number("0-14")
        self.assertEqual(14, servo_number.servo_number)

        with self.assertRaises(AssertionError) as e:
            self.machine.default_platform._parse_servo_number("0-1")
            self.machine.default_platform._parse_servo_number("0-9")
            self.machine.default_platform._parse_servo_number("0-15")

        # go to min position
        self.controller.expected_commands = {
                "PSC011003": None
        }
        self.machine.servos["servo1"].go_to_position(0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # go to max position
        self.controller.expected_commands = {
                "PSC011027": None
        }
        self.machine.servos["servo1"].go_to_position(1)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _switch_hit_cb(self, **kwargs):
        self.switch_hit = True

    def test_switches(self):
        # test initial switch states (based on PSA command response)
        self.assertSwitchState("s_test_1", 1)
        self.assertSwitchState("s_test_2", 1)
        self.assertSwitchState("s_test_3", 0)
        self.assertSwitchState("s_test_4", 0)
        self.assertSwitchState("s_test_11", 0)
        self.assertSwitchState("s_test_12", 0)
        self.assertSwitchState("s_test_13", 1)
        self.assertSwitchState("s_test_14", 1)

        self._test_switch_changes()
        self._test_switch_changes_nc()
        self._test_switch_configure()

    def _test_switch_configure(self):
        # configuring switches in PKONE does not generate any commands between the host and controller

        # last switch on first board
        self.machine.default_platform.configure_switch('0-35', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('0-36', SwitchConfig(name="", debounce='auto', invert=0), {})

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('4-1', SwitchConfig(name="", debounce='auto', invert=0), {})

        # invalid switch (switch number begin at 1 and not 0)
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('0-0', SwitchConfig(name="", debounce='auto', invert=0), {})

    def _test_switch_changes(self):
        self.assertIsInstance(self.machine.default_platform, PKONEHardwarePlatform)
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test", 0)
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("PSW0071E")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_test", 1)
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 1)

        self.machine.default_platform.process_received_message("PSW0070E")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 0)

    def _test_switch_changes_nc(self):
        self.assertIsInstance(self.machine.default_platform, PKONEHardwarePlatform)
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test_nc", 1)
        self.assertFalse(self.switch_hit)

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 1)

        self.machine.default_platform.process_received_message("PSW0261E")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 0)

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.process_received_message("PSW0260E")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 1)
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.controller.expected_commands = {
            "PCC1010109900000": None,
            "PCP101": None,
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual enable no hw rule
        self.controller.expected_commands = {
            "PCH101": None,
            "PCC1010109912000": None
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual disable no hw rule
        self.controller.expected_commands = {
            "PCR101": None
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # flipper rule enable
        self.controller.expected_commands = {
            "PHR10140500000000119912000": None
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip with hw rule in action
        self.controller.expected_commands = {
            "PCP101": None  # pulse (no need to configure because config did not change)
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip with hw rule in action without reconfigure (same pulse)
        self.controller.expected_commands = {
            "PCC1010119912000": None,       # reconfigure coil
            "PCP101": None,                 # pulse
        }
        self.machine.coils["c_flipper_main"].pulse(11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual enable with hw rule (same pulse)
        self.controller.expected_commands = {
            "PCH101": None      # pulse (config did not change so no config msg necessary)
        }
        self.machine.coils["c_flipper_main"].enable(pulse_ms=11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual disable with hw rule
        self.controller.expected_commands = {
            "PCR101": None,
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual enable with hw rule (different pulse)
        self.controller.expected_commands = {
            "PCC1010109912000": None,       # configure + enable
            "PCH101": None
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual disable with hw rule
        self.controller.expected_commands = {
            "PCR101": None
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # disable rule
        self.controller.expected_commands = {
            "PHD101": None
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip no hw rule (config is still cached)
        self.controller.expected_commands = {
            "PCP101": None
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # manual flip again with cached config
        self.controller.expected_commands = {
            "PCP101": None
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_flipper_two_coils(self):
        # we pulse the main coil
        # hold coil is pulsed + enabled
        self.controller.expected_commands = {
            "PHR10130500000000109900000": None,
            "PHR10240500000000109912000": None,
        }
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        self.controller.expected_commands = {
            "PHD101": None,
            "PHD102": None
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def test_leds(self):
        self._test_simple_led()
        self._test_led_hardware_alignment()
        self._test_ws281x_led()

    def _test_simple_led(self):
        self.assertTrue("test_simple_led" in self.machine.lights)
        self.assertTrue("test_other_simple_led" in self.machine.lights)

        # test enable of simple led
        self.controller.expected_commands = {
            "PLS2171": None,
            "PLS3011": None,
        }
        self.machine.lights["test_simple_led"].on()
        self.machine.lights["test_other_simple_led"].on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test disable of simple led
        self.controller.expected_commands = {
            "PLS2170": None,
            "PLS3010": None,
        }
        self.machine.lights["test_simple_led"].off()
        self.machine.lights["test_other_simple_led"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test turning on of simple led using color
        self.controller.expected_commands = {
            "PLS2171": None,
            "PLS3011": None,
        }
        self.machine.lights["test_simple_led"].color(RGBColor("FFFFFF"))
        self.machine.lights["test_other_simple_led"].color(RGBColor("FFFFFF"))
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

        # test turning off of simple led using color
        self.controller.expected_commands = {
            "PLS2170": None,
            "PLS3010": None,
        }
        self.machine.lights["test_simple_led"].color(RGBColor("000000"))
        self.machine.lights["test_other_simple_led"].color(RGBColor("000000"))
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)

    def _test_ws281x_led(self):
        self.advance_time_and_run()

        # get light devices
        device_rgb_1 = self.machine.lights["test_rgb_led_1"]
        device_rgb_2 = self.machine.lights["test_rgb_led_2"]
        device_rgb_3 = self.machine.lights["test_rgb_led_3"]
        device_rgb_4 = self.machine.lights["test_rgb_led_4"]

        device_rgbw_1 = self.machine.lights["test_rgbw_led_1"]
        device_rgbw_2 = self.machine.lights["test_rgbw_led_2"]
        device_rgbw_3 = self.machine.lights["test_rgbw_led_3"]
        device_rgbw_4 = self.machine.lights["test_rgbw_led_4"]

        # ensure channel numbers (hardware drivers) have been assigned correctly
        self.assertListEqual(["2-1-0", "2-1-1", "2-1-2"], device_rgb_1.get_hw_numbers())
        self.assertListEqual(["2-1-3", "2-1-4", "2-1-5"], device_rgb_2.get_hw_numbers())
        self.assertListEqual(["2-1-6", "2-1-7", "2-1-8", "2-1-9"], device_rgb_3.get_hw_numbers())
        self.assertListEqual(["2-1-10", "2-1-11", "2-1-12"], device_rgb_4.get_hw_numbers())

        self.assertListEqual(["3-1-0", "3-1-1", "3-1-2", "3-1-3"], device_rgbw_1.get_hw_numbers())
        self.assertListEqual(["3-1-4", "3-1-5", "3-1-6", "3-1-7"], device_rgbw_2.get_hw_numbers())
        self.assertListEqual(["3-1-8", "3-1-9", "3-1-10"], device_rgbw_3.get_hw_numbers())
        self.assertListEqual(["3-1-11", "3-1-12", "3-1-13", "3-1-14"], device_rgbw_4.get_hw_numbers())

        # ensure channels were properly added to the Lightshow boards
        self.assertIsInstance(self.machine.default_platform, PKONEHardwarePlatform)
        rgb_hw_channels = self.machine.default_platform.pkone_lightshows[2].get_all_channel_hw_drivers()
        rgbw_hw_channels = self.machine.default_platform.pkone_lightshows[3].get_all_channel_hw_drivers()
        self.assertEqual(13, len(rgb_hw_channels))
        self.assertEqual(15, len(rgbw_hw_channels))

        # ensure all LEDs are initially off
        self.assertLightColor("test_rgb_led_1", RGBColor("off"))
        self.assertLightColor("test_rgb_led_2", RGBColor("off"))
        self.assertLightColor("test_rgb_led_3", RGBColor("off"))
        self.assertLightColor("test_rgb_led_4", RGBColor("off"))

        self.assertLightColor("test_rgbw_led_1", RGBColor("off"))
        self.assertLightColor("test_rgbw_led_2", RGBColor("off"))
        self.assertLightColor("test_rgbw_led_3", RGBColor("off"))
        self.assertLightColor("test_rgbw_led_4", RGBColor("off"))

        # test turning on rgb led using color
        self.controller.expected_commands = {
            "PLB2101020000255000000000000255": None,
        }
        self.machine.lights["test_rgb_led_1"].color(RGBColor("red"))
        self.machine.lights["test_rgb_led_2"].color(RGBColor("blue"))
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning on rgb led using color with fade
        self.controller.expected_commands = {
            "PLB2101020012000128000255000000": None,
        }
        self.machine.lights["test_rgb_led_1"].color(RGBColor("green"), 123)
        self.machine.lights["test_rgb_led_2"].color(RGBColor("red"), 123)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning on rgb led out of hardware alignment using color
        self.controller.expected_commands = {
            "PLB2103020000255192203192000000": None,
        }
        self.machine.lights["test_rgb_led_3"].color(RGBColor("pink"))
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning off rgb led
        self.controller.expected_commands = {
            "PLB2101050000000000000000000000000000000000000000000000000": None,
        }
        self.machine.lights["test_rgb_led_1"].off()
        self.machine.lights["test_rgb_led_2"].off()
        self.machine.lights["test_rgb_led_3"].off()
        self.machine.lights["test_rgb_led_4"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning on rgb led out of hardware alignment using color with fade (uses software fade)
        self.controller.validate_expected_commands_mode = False
        self.machine.lights["test_rgb_led_3"].color(RGBColor("pink"), 250)
        self.advance_time_and_run(.5)
        self.assertEqual(14, len(self.controller.sent_commands))
        self.assertEqual("PLB2103020000000000000000000000", self.controller.sent_commands[0])
        self.assertEqual("PLB2103020000255192203192000000", self.controller.sent_commands[-1])
        self.controller.reset()

        # test turning off rgb led out of hardware alignment with fade (uses software fade) and turning on
        # an rgb led in alignment with color simultaneously (uses hardware fade)
        self.controller.validate_expected_commands_mode = False
        self.machine.lights["test_rgb_led_1"].color(RGBColor("blue"), 250)
        self.machine.lights["test_rgb_led_3"].off(250)
        self.advance_time_and_run(.5)
        self.assertEqual(15, len(self.controller.sent_commands))
        self.assertEqual("PLB2101010025000000255", self.controller.sent_commands[0])
        self.assertEqual("PLB2103020000255192203192000000", self.controller.sent_commands[1])
        self.assertEqual("PLB2103020000000000000000000000", self.controller.sent_commands[-1])
        self.controller.reset()

        # test turning on rgbw led using color
        self.controller.expected_commands = {
            "PWB3101020000255000000000000000255000": None,
        }
        self.machine.lights["test_rgbw_led_1"].color(RGBColor("red"))
        self.machine.lights["test_rgbw_led_2"].color(RGBColor("blue"))
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning on rgbw led using color with fade
        self.controller.expected_commands = {
            "PWB3101020012000128000000255000000000": None,
        }
        self.machine.lights["test_rgbw_led_1"].color(RGBColor("green"), 128)
        self.machine.lights["test_rgbw_led_2"].color(RGBColor("red"), 128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning on rgbw led out of hardware alignment using color
        self.controller.expected_commands = {
            "PWB3103010000255192203000": None,
        }
        self.machine.lights["test_rgbw_led_3"].color(RGBColor("pink"))
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning off rgbw led
        self.controller.expected_commands = {
            "PWB3101040000000000000000000000000000000000000000000000000000": None,
        }
        self.machine.lights["test_rgbw_led_1"].off()
        self.machine.lights["test_rgbw_led_2"].off()
        self.machine.lights["test_rgbw_led_3"].off()
        self.machine.lights["test_rgbw_led_4"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.controller.expected_commands)
        self.controller.reset()

        # test turning on rgbw led out of hardware alignment using color with fade (uses software fade)
        self.controller.validate_expected_commands_mode = False
        self.machine.lights["test_rgbw_led_3"].color(RGBColor("pink"), 250)
        self.advance_time_and_run(.5)
        self.assertEqual(14, len(self.controller.sent_commands))
        self.assertEqual("PWB3103010000000000000000", self.controller.sent_commands[0])
        self.assertEqual("PWB3103010000255192203000", self.controller.sent_commands[-1])
        self.controller.reset()

        # test turning off rgbw led out of hardware alignment with fade (uses software fade) and turning on
        # an rgbw led in alignment with color simultaneously (uses hardware fade)
        self.controller.validate_expected_commands_mode = False
        self.machine.lights["test_rgbw_led_1"].color(RGBColor("blue"), 250)
        self.machine.lights["test_rgbw_led_3"].off(250)
        self.advance_time_and_run(.5)
        self.assertEqual(15, len(self.controller.sent_commands))
        self.assertEqual("PWB3101010025000000255000", self.controller.sent_commands[0])
        self.assertEqual("PWB3103010000255192203000", self.controller.sent_commands[1])
        self.assertEqual("PWB3103010000000000000000", self.controller.sent_commands[-1])
        self.controller.reset()

    def _test_led_hardware_alignment(self):
        self.assertIsInstance(self.machine.default_platform, PKONEHardwarePlatform)
        self.assertTrue(self.machine.default_platform._led_is_hardware_aligned("test_rgb_led_1"))
        self.assertTrue(self.machine.default_platform._led_is_hardware_aligned("test_rgb_led_2"))
        self.assertFalse(self.machine.default_platform._led_is_hardware_aligned("test_rgb_led_3"))
        self.assertFalse(self.machine.default_platform._led_is_hardware_aligned("test_rgb_led_4"))
        self.assertTrue(self.machine.default_platform._led_is_hardware_aligned("test_rgbw_led_1"))
        self.assertTrue(self.machine.default_platform._led_is_hardware_aligned("test_rgbw_led_2"))
        self.assertFalse(self.machine.default_platform._led_is_hardware_aligned("test_rgbw_led_3"))
        self.assertFalse(self.machine.default_platform._led_is_hardware_aligned("test_rgbw_led_4"))

