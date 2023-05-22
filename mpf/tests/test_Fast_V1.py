from mpf.core.platform import SwitchConfig
from mpf.core.rgb_color import RGBColor
from mpf.exceptions.config_file_error import ConfigFileError

from mpf.tests.MpfTestCase import MagicMock, test_config, expect_startup_error
from mpf.tests.test_Fast import TestFast

class TestFastV1(TestFast):
    """FAST Platform class for a networked V1 platform. Tests the NET v1 and RGB processors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.net_cpu = None
        self.rgb_cpu = None

    def get_config_file(self):
        return 'config_v1.yaml'

    def create_expected_commands(self):
        self.net_cpu.expected_commands = {
            'NN:00': 'NN:00,FP-I/O-3208-2   ,01.00,08,20,04,06,00,00,00,00',     # 3208 board
            'NN:01': 'NN:01,FP-I/O-0804-1   ,01.00,04,08,04,06,00,00,00,00',     # 0804 board
            'NN:02': 'NN:02,FP-I/O-1616-2   ,01.00,10,10,04,06,00,00,00,00',     # 1616 board
            'NN:03': 'NN:03,FP-I/O-1616-2   ,01.00,10,10,04,06,00,00,00,00',     # 1616 board
            'NN:04': 'NN:04,,,,,,,,,,',     # no board
            "SN:01,01,04,04": "SN:P",
            "SN:02,01,04,04": "SN:P",
            "SN:03,01,04,04": "SN:P",
            "SN:0B,01,04,04": "SN:P",
            "SN:0C,01,04,04": "SN:P",
            "SN:16,01,04,04": "SN:P",
            "SN:07,01,1A,05": "SN:P",
            "SN:1A,01,04,04": "SN:P",
            "SN:39,01,04,04": "SN:P",
            "DN:01,00,00,00": "DN:P",
            "DN:04,00,00,00": "DN:P",
            "DN:06,00,00,00": "DN:P",
            "DN:07,00,00,00": "DN:P",
            "DN:11,00,00,00": "DN:P",
            "DN:12,00,00,00": "DN:P",
            "DN:13,00,00,00": "DN:P",
            "DN:16,00,00,00": "DN:P",
            "DN:17,00,00,00": "DN:P",
            "DN:20,00,00,00": "DN:P",
            "DN:21,00,00,00": "DN:P",
            "DN:01,C1,00,18,00,FF,FF,00": "DN:P",   # configure digital output
            }

        self.rgb_cpu.expected_commands = {
            "RF:0": "RF:P",
            "RA:000000": "RA:P",
            "RF:00": "RF:P",
            }

    def setUp(self):
        super().setUp()
        if not self.startup_error:
            self.advance_time_and_run()
            self.assertFalse(self.net_cpu.expected_commands)
            self.assertFalse(self.rgb_cpu.expected_commands)
            self.assertFalse(self.seg_cpu.expected_commands)

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
        self._test_timed_enable()
        self._test_default_timed_enable()
        self._test_enable_exception()
        self._test_allow_enable()
        self._test_pwm_ssm()
        self._test_coil_configure()

        # test hardware scan
        info_str = """NET CPU: NET FP-CPU-002-2 01.05
RGB CPU: RGB FP-CPU-002-2 00.89
No connection to the Audio Controller.
Segment Controller: SEG FP-CPU-002-2 00.10
No connection to the Expansion Bus.

Boards:
Board 0 - Model: FP-I/O-3208-2    Firmware: 01.00 Switches: 32 Drivers: 8
Board 1 - Model: FP-I/O-0804-1    Firmware: 01.00 Switches: 8 Drivers: 4
Board 2 - Model: FP-I/O-1616-2    Firmware: 01.00 Switches: 16 Drivers: 16
Board 3 - Model: FP-I/O-1616-2    Firmware: 01.00 Switches: 16 Drivers: 16
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_coil_configure(self):
        self.assertEqual("FAST Board 0", self.machine.coils["c_test"].hw_driver.get_board_name())
        self.assertEqual("FAST Board 3", self.machine.coils["c_flipper_hold"].hw_driver.get_board_name())
        # last driver on board
        self.net_cpu.expected_commands = {
            "DN:2B,00,00,00": "DN:P"
        }
        coil = self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '1616_2-15',
                                                              {"connection": "network", "recycle_ms": 10})
        self.assertEqual('2B', coil.number)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # board 0 has 8 drivers. configuring driver 9 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '3208-8',
                                                           {"connection": "network", "recycle_ms": 10})

        # test error for invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, 'brian-0',
                                                           {"connection": "network", "recycle_ms": 10})

        # test error for driver number too high
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, '3208-9',
                                                           {"connection": "network", "recycle_ms": 10})

    def _test_pulse(self):
        self.net_cpu.expected_commands = {
            "DN:04,89,00,10,17,FF,00,00,00": "DN:P"
        }
        # pulse coil 4
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_long_pulse(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DN:12,C1,00,18,00,FF,FF,00": "DN:P"
        }
        self.machine.coils["c_long_pulse"].pulse()
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

    def _test_timed_enable(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DN:16,89,00,10,14,FF,C8,88,00": "DN:P"
        }
        self.machine.coils["c_timed_enable"].timed_enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_default_timed_enable(self):
        # enable command
        self.net_cpu.expected_commands = {
            "DN:17,89,00,10,14,FF,C8,88,00": "DN:P"
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
            "DN:06,C1,00,18,17,FF,FF,00": "DN:P"
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_pwm_ssm(self):
        self.net_cpu.expected_commands = {
            "DN:13,C1,00,18,0A,FF,84224244,00": "DN:P"
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
            "DN:21,01,07,10,0A,FF,00,00,14": "DN:P"
        }
        # coil and switch are on different boards but first 8 switches always work
        self.machine.autofire_coils["ac_different_boards"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # switch and coil on board 3. should work
        self.net_cpu.expected_commands = {
            "DN:21,01,39,10,0A,FF,00,00,14": "DN:P",
            "SN:39,01,02,02": "SN:P"
        }
        self.machine.autofire_coils["ac_board_3"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:10,01,03,10,0A,89,00,00,14": "DN:P",
        }
        # coil and switch are on different boards
        with self.assertRaises(AssertionError):
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
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:07,81": "DN:P"
        }
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_pwm32(self):
        self.net_cpu.expected_commands = {
            "DN:11,89,00,10,0A,AAAAAAAA,00,00,00": "DN:P"
        }
        self.machine.coils["c_pulse_pwm32_mask"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:11,C1,00,18,0A,AAAAAAAA,4A4A4A4A,00": "DN:P"
        }
        self.machine.coils["c_pulse_pwm32_mask"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.net_cpu.expected_commands = {
            "DN:07,11,1A,10,0A,FF,00,00,14": "DN:P",
            "SN:1A,01,02,02": "SN:P"
        }
        self.machine.autofire_coils["ac_inverted_switch"].enable()
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
        self.machine.default_platform.configure_switch('3208-31', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('3208-32', SwitchConfig(name="", debounce='auto', invert=0), {})

        self.net_cpu.expected_commands = {
            "SN:47,01,04,04": "SN:P"
        }
        self.machine.default_platform.configure_switch('1616_2-15', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('brian-0', SwitchConfig(name="", debounce='auto', invert=0), {})

        # invalid switch number
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('3208-33', SwitchConfig(name="", debounce='auto', invert=0), {})

    def _test_switch_changes(self):
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_flipper_eos", 1)

        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test", 0)
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-N:07\r")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_test", 1)
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 1)

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/N:07\r")
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

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-N:1A\r")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 0)

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/N:1A\r")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 1)
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,89,00,10,0A,FF,00,00,00": "DN:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00": "DN:P"
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable no hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P"
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # flipper rule enable
        self.net_cpu.expected_commands = {
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",
            "SN:01,01,02,02": "SN:P"
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action
        self.net_cpu.expected_commands = {
            "DN:20,89,00,10,0A,FF,00,00,00": "DN:P",    # configure and pulse
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",    # restore rule
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action without reconfigure (same pulse)
        self.net_cpu.expected_commands = {
            "TN:20,01": "TN:P",                         # pulse
        }
        self.machine.coils["c_flipper_main"].pulse(11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (same pulse)
        self.net_cpu.expected_commands = {
            "TN:20,03": "TN:P"
        }
        self.machine.coils["c_flipper_main"].enable(pulse_ms=11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P",
            "TN:20,00": "TN:P"   # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (different pulse)
        self.net_cpu.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00": "DN:P",       # configure pwm + enable
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P",
            "DN:20,01,01,18,0B,FF,01,00,00": "DN_P",    # configure rules
            "TN:20,00": "TN:P"                          # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # disable rule
        self.net_cpu.expected_commands = {
            "DN:20,81": "DN:P"
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,89,00,10,0A,FF,00,00,00": "DN:P"
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip again with cached config
        self.net_cpu.expected_commands = {
            "TN:20,01": "TN:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
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
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:20,81": "DN:P",
            "DN:21,81": "DN:P"
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def test_bootloader_crash(self):
        # Test that the machine stops if the RGB processor sends a bootloader msg
        self.machine.stop = MagicMock()
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"!B:00\r")
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.stop.called)

    def test_bootloader_crash_ignored(self):
        # Test that RGB processor bootloader msgs can be ignored
        self.machine.default_platform.config['ignore_rgb_crash'] = True
        self.mock_event('fast_rgb_rebooted')
        self.machine.stop = MagicMock()
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"!B:00\r")
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.stop.called)
        self.assertEventCalled('fast_rgb_rebooted')

    def test_leds(self):
        self.advance_time_and_run()
        device = self.machine.lights["test_led"]
        device2 = self.machine.lights["test_led2"]
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['98'])
        # test led on
        device.on()
        self.advance_time_and_run(1)
        self.assertEqual("FFFFFF", self.rgb_cpu.leds['97'])
        self.assertEqual("000000", self.rgb_cpu.leds['98'])

        device2.color("001122")

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])
        self.assertEqual("110022", self.rgb_cpu.leds['98'])  # GRB so ensure it's not 001122

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("17022A", self.rgb_cpu.leds['97'])  # GRB so ensure it's not 001122

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['97'])

        self.advance_time_and_run(.02)

        # fade led over 100ms
        device.color(RGBColor((100, 100, 100)), fade_ms=100)
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

    @expect_startup_error()
    @test_config("error_lights.yaml")
    def test_light_errors(self):
        self.assertIsInstance(self.startup_error, ConfigFileError)
        self.assertEqual(7, self.startup_error.get_error_no())
        self.assertEqual("light.test_led", self.startup_error.get_logger_name())
        self.assertIsInstance(self.startup_error.__cause__, ConfigFileError)
        self.assertEqual(9, self.startup_error.__cause__.get_error_no())
        self.assertEqual("FAST", self.startup_error.__cause__.get_logger_name())
        self.assertEqual("Light syntax is number-channel (but was \"3\") for light test_led.",
                         self.startup_error.__cause__._message)