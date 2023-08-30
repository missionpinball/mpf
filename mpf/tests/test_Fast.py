# mpf.tests.test_Fast

from mpf.core.platform import SwitchConfig
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.platforms.fast import MockFastNetNeuron, MockFastExp, MockFastDmd, MockFastSeg, MockFastRgb, MockFastNetNano


class TestFast(MpfTestCase):
    """Tests the current FAST modern platforms. Tests for Net v2 (Modern & Retro), SEG, and DMD processors."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net2', 'seg', 'dmd']
        self.serial_connections = dict()

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/fast/'

    def get_platform(self):
        return False

    def _mock_loop(self):
        for conn in self.serial_connections.values():
            self.clock.mock_serial(conn.port, conn)

    def create_connections(self):

        for conn in self.serial_connections_to_mock:
            if conn == 'net2':
                self.serial_connections['net2'] = MockFastNetNeuron()  # default com3
            elif conn == 'exp':
                self.serial_connections['exp'] = MockFastExp(self)  # default com4
            elif conn == 'rgb':
                self.serial_connections['rgb'] = MockFastRgb()  # default com5
            elif conn == 'net1':
                self.serial_connections['net1'] = MockFastNetNano()  # default com6
            elif conn == 'seg':
                self.serial_connections['seg'] = MockFastSeg()  # default com7
            elif conn == 'dmd':
                self.serial_connections['dmd'] = MockFastDmd()  # default com8

    def create_expected_commands(self):

        self.serial_connections['net2'].attached_boards = {
            'NN:00': 'NN:00,FP-I/O-3208-3   ,01.09,08,20,00,00,00,00,00,00',     # 3208 board
            'NN:01': 'NN:01,FP-I/O-0804-3   ,01.09,04,08,00,00,00,00,00,00',     # 0804 board
            'NN:02': 'NN:02,FP-I/O-1616-3   ,01.09,10,10,00,00,00,00,00,00',     # 1616 board
            'NN:03': 'NN:03,FP-I/O-1616-3   ,01.09,10,10,00,00,00,00,00,00',     # 1616 board
            'NN:04': 'NN:04,FP-I/O-0024-3   ,01.10,08,18,00,00,00,00,00,00',     # Cab I/O board
            }

        self.serial_connections['net2'].expected_commands = {
            **self.serial_connections['net2'].attached_boards,
            "SL:01,01,04,04": "SL:P",
            "SL:02,01,04,04": "SL:P",
            "SL:03,01,04,04": "SL:P",
            "SL:07,01,1A,05": "SL:P",
            "SL:0B,01,04,04": "SL:P",
            "SL:0C,01,04,04": "SL:P",
            "SL:16,01,04,04": "SL:P",
            "SL:1A,01,04,04": "SL:P",
            "SL:39,01,04,05": "SL:P",

            "DL:01,00,00,00": "DL:P",
            "DL:01,C1,00,18,00,FF,FF,00": "DL:P",
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
            }

        self.serial_connections['net2'].expected_commands['SL:L'] = (
            'SL:68\r'
            'SL:00,02,01,02\r'
            'SL:01,01,03,04\r'
            'SL:02,01,02,14\r'
            'SL:03,01,02,14\r'
            'SL:04,01,02,14\r'
            'SL:05,01,02,14\r'
            'SL:06,01,02,14\r'
            'SL:07,01,02,14\r'
            'SL:08,01,02,14\r'
            'SL:09,01,02,14\r'
            'SL:0A,01,02,14\r'
            'SL:0B,01,02,14\r'
            'SL:0C,01,02,14\r'
            'SL:0D,01,02,14\r'
            'SL:0E,01,02,14\r'
            'SL:0F,01,02,14\r'
            'SL:10,01,02,14\r'
            'SL:11,01,02,14\r'
            'SL:12,01,02,14\r'
            'SL:13,01,02,14\r'
            'SL:14,01,02,14\r'
            'SL:15,01,02,14\r'
            'SL:16,01,02,14\r'
            'SL:17,01,02,14\r'
            'SL:18,01,02,14\r'
            'SL:19,01,02,14\r'
            'SL:1A,01,02,14\r'
            'SL:1B,01,02,14\r'
            'SL:1C,01,02,14\r'
            'SL:1D,01,02,14\r'
            'SL:1E,01,02,14\r'
            'SL:1F,01,02,14\r'
            'SL:20,01,02,14\r'
            'SL:21,01,02,14\r'
            'SL:22,01,02,14\r'
            'SL:23,01,02,14\r'
            'SL:24,01,02,14\r'
            'SL:25,01,02,14\r'
            'SL:26,01,02,14\r'
            'SL:27,01,02,14\r'
            'SL:28,01,02,14\r'
            'SL:29,01,02,14\r'
            'SL:2A,01,02,14\r'
            'SL:2B,01,02,14\r'
            'SL:2C,01,02,14\r'
            'SL:2D,01,02,14\r'
            'SL:2E,01,02,14\r'
            'SL:2F,01,02,14\r'
            'SL:30,01,02,14\r'
            'SL:31,01,02,14\r'
            'SL:32,01,02,14\r'
            'SL:33,01,02,14\r'
            'SL:34,01,02,14\r'
            'SL:35,01,02,14\r'
            'SL:36,01,02,14\r'
            'SL:37,01,02,14\r'
            'SL:38,01,02,14\r'
            'SL:39,01,02,14\r'
            'SL:3A,01,02,14\r'
            'SL:3B,01,02,14\r'
            'SL:3C,01,02,14\r'
            'SL:3D,01,02,14\r'
            'SL:3E,01,02,14\r'
            'SL:3F,01,02,14\r'
            'SL:40,01,02,14\r'
            'SL:41,01,02,14\r'
            'SL:42,01,02,14\r'
            'SL:43,01,02,14\r'
            'SL:44,01,02,14\r'
            'SL:45,01,02,14\r'
            'SL:46,01,02,14\r'
            'SL:47,01,02,14\r'
            'SL:48,01,02,14\r'
            'SL:49,01,02,14\r'
            'SL:4A,01,02,14\r'
            'SL:4B,01,02,14\r'
            'SL:4C,01,02,14\r'
            'SL:4D,01,02,14\r'
            'SL:4E,01,02,14\r'
            'SL:4F,01,02,14\r'
            'SL:50,01,02,14\r'
            'SL:51,01,02,14\r'
            'SL:52,01,02,14\r'
            'SL:53,01,02,14\r'
            'SL:54,01,02,14\r'
            'SL:55,01,02,14\r'
            'SL:56,01,02,14\r'
            'SL:57,01,02,14\r'
            'SL:58,01,02,14\r'
            'SL:59,01,02,14\r'
            'SL:5A,01,02,14\r'
            'SL:5B,01,02,14\r'
            'SL:5C,01,02,14\r'
            'SL:5D,01,02,14\r'
            'SL:5E,01,02,14\r'
            'SL:5F,01,02,14\r'
            'SL:60,01,02,14\r'
            'SL:61,01,02,14\r'
            'SL:62,01,02,14\r'
            'SL:63,01,02,14\r'
            'SL:64,01,02,14\r'
            'SL:65,01,02,14\r'
            'SL:66,01,02,14\r'
            'SL:67,01,02,14\r'
            )

    def tearDown(self):
        super().tearDown()
        if not self.startup_error:
            for name, conn in self.serial_connections.items():
                self.assertFalse(conn.expected_commands,
                                 f"Expected commands for {name} are not empty: {conn.expected_commands}")

    def setUp(self):
        self.expected_duration = 2
        self.create_connections()
        self.create_expected_commands()
        super().setUp()

        if not self.startup_error:
            self.advance_time_and_run()
            self.assertEqual(5, len(self.machine.default_platform.io_boards))
            self.assertEqual(32, self.machine.default_platform.io_boards[0].switch_count)
            self.assertEqual(8, self.machine.default_platform.io_boards[0].driver_count)
            self.assertEqual(8, self.machine.default_platform.io_boards[1].switch_count)
            self.assertEqual(4, self.machine.default_platform.io_boards[1].driver_count)
            self.assertEqual(16, self.machine.default_platform.io_boards[2].switch_count)
            self.assertEqual(16, self.machine.default_platform.io_boards[2].driver_count)
            self.assertEqual(16, self.machine.default_platform.io_boards[3].switch_count)
            self.assertEqual(16, self.machine.default_platform.io_boards[3].driver_count)
            self.assertEqual(24, self.machine.default_platform.io_boards[4].switch_count)
            self.assertEqual(8, self.machine.default_platform.io_boards[4].driver_count)

            for conn in self.serial_connections.values():
                self.assertFalse(conn.expected_commands)

        # If a test is testing a bad config file and causes a startup exception,
        # the machine will shut down. Safety check before we add futures to the loop.
        if not self.machine.is_shutting_down:
            self.advance_time_and_run(1)

    def test_coils(self):
        self._test_coil_configure()
        # self._test_pulse()
        # self._test_long_pulse()
        # self._test_timed_enable()
        # self._test_default_timed_enable()
        # self._test_enable_exception()
        # self._test_allow_enable()
        # self._test_pwm_ssm()

        # test hardware scan
        info_str = (
            'DMD: FP-CPU-002-2 v00.88\r'
            'NET: FP-CPU-2000 v02.13\r'
            'SEG: FP-CPU-002-2 v00.10\r'
            '\r'
            'I/O Boards:\r'
            'Board 0 - Model: FP-I/O-3208 Firmware: 01.09 Switches: 32 Drivers: 8\r'
            'Board 1 - Model: FP-I/O-0804 Firmware: 01.09 Switches: 8 Drivers: 4\r'
            'Board 2 - Model: FP-I/O-1616 Firmware: 01.09 Switches: 16 Drivers: 16\r'
            'Board 3 - Model: FP-I/O-1616 Firmware: 01.09 Switches: 16 Drivers: 16\r'
            'Board 4 - Model: FP-I/O-0024 Firmware: 01.10 Switches: 24 Drivers: 8\r'
            )

        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_coil_configure(self):
        self.assertEqual("FAST Board 0", self.machine.coils["c_test"].hw_driver.get_board_name())
        self.assertEqual("FAST Board 3", self.machine.coils["c_flipper_hold"].hw_driver.get_board_name())
        # last driver on board
        self.serial_connections['net2'].expected_commands = {
            "DL:2B,00,00,00": "DL:P"
        }
        coil = self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, 'io1616lower-15',
                                                              {"connection": "network", "recycle_ms": 10})
        self.assertEqual('2B', coil.number)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # board 0 has 8 drivers. configuring driver 9 should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, 'io3208-8',
                                                           {"connection": "network", "recycle_ms": 10})

        # test error for invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, 'brian-0',
                                                           {"connection": "network", "recycle_ms": 10})

        # test error for driver number too high
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_driver(self.machine.coils["c_test"].hw_driver.config, 'io3208-9',
                                                           {"connection": "network", "recycle_ms": 10})

    def _test_pulse(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:04,81,00,10,17,FF,00,00,00": "DL:P",  # initial config
            "TL:04,01": "TL:P"  # manual pulse
        }
        # pulse coil 4
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_long_pulse(self):
        # enable command
        self.serial_connections['net2'].expected_commands = {
            "DL:12,C1,00,18,00,FF,FF,00": "DL:P"
        }
        self.machine.coils["c_long_pulse"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # disable command
        self.serial_connections['net2'].expected_commands = {
            "TL:12,02": "TL:P"
        }

        self.advance_time_and_run(1)
        # pulse_ms is 2000ms, so after 1s, this should not be sent
        self.assertTrue(self.serial_connections['net2'].expected_commands)

        self.advance_time_and_run(1)
        # but after 2s, it should be
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_timed_enable(self):
        # enable command
        self.serial_connections['net2'].expected_commands = {
            "DL:16,89,00,10,14,FF,C8,88,00": "DL:P"
        }
        self.machine.coils["c_timed_enable"].timed_enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_default_timed_enable(self):
        # enable command
        self.serial_connections['net2'].expected_commands = {
            "DL:17,89,00,10,14,FF,C8,88,00": "DL:P"
        }
        self.machine.coils["c_default_timed_enable"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils["c_test"].enable()
            self.advance_time_and_run(.1)

    def _test_allow_enable(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:06,C1,00,18,17,FF,FF,00": "DL:P"
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_pwm_ssm(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:13,C1,00,18,0A,FF,84224244,00": "DL:P"
        }
        self.machine.coils["c_hold_ssm"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def DISABLED_test_rules(self):
        self._test_enable_exception_hw_rule()
        self._test_two_rules_one_switch()
        self._test_hw_rule_pulse()
        self._test_hw_rule_pulse_pwm32()
        self._test_hw_rule_pulse_inverted_switch()
        self._test_hw_rule_same_board()

    def _test_hw_rule_same_board(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:21,01,07,10,0A,FF,00,00,14": "DL:P"
        }
        # coil and switch are on different boards but first 8 switches always work
        self.machine.autofire_coils["ac_different_boards"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # switch and coil on board 3. should work
        self.serial_connections['net2'].expected_commands = {
            "DL:21,01,39,10,0A,FF,00,00,14": "DL:P",
            "SL:39,01,02,02": "SL:P"
        }
        self.machine.autofire_coils["ac_board_3"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
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
        self.serial_connections['net2'].expected_commands = {
            "SL:03,01,02,02": "SL:P",
            "DL:04,01,03,10,17,FF,00,00,1B": "DL:P",
            "DL:06,01,03,10,17,FF,00,00,2E": "DL:P"
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_hw_rule_pulse(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:07,01,16,10,0A,FF,00,00,14": "DL:P",  # hw rule
            "SL:16,01,02,02": "SL:P"                  # debounce quick on switch
        }
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "DL:07,81": "DL:P"
        }
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_hw_rule_pulse_pwm32(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:11,89,00,10,0A,AAAAAAAA,00,00,00": "DL:P"
        }
        self.machine.coils["c_pulse_pwm32_mask"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "DL:11,C1,00,18,0A,AAAAAAAA,4A4A4A4A,00": "DL:P"
        }
        self.machine.coils["c_pulse_pwm32_mask"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:07,11,1A,10,0A,FF,00,00,14": "DL:P",
            "SL:1A,01,02,02": "SL:P"
        }
        self.machine.autofire_coils["ac_inverted_switch"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def _switch_hit_cb(self, **kwargs):
        self.switch_hit = True

    def DISABLED_test_switches(self):
        self._test_switch_changes()
        self._test_switch_changes_nc()
        self._test_switch_configure()

    def _test_switch_configure(self):
        # last switch on first board
        self.serial_connections['net2'].expected_commands = {
            "SL:1F,01,04,04": "SL:P"
        }
        self.machine.default_platform.configure_switch('io3208-31', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # next should not work
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('io3208-32', SwitchConfig(name="", debounce='auto', invert=0), {})

        self.serial_connections['net2'].expected_commands = {
            "SL:47,01,04,04": "SL:P"
        }
        self.machine.default_platform.configure_switch('io1616lower-15', SwitchConfig(name="", debounce='auto', invert=0), {})
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('brian-0', SwitchConfig(name="", debounce='auto', invert=0), {})

        # switch number higher than board supports
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('io3208-33', SwitchConfig(name="", debounce='auto', invert=0), {})

    def _test_switch_changes(self):
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_flipper_eos", 1)

        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test", 0)
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-L:07\r")
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-L:07\r")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_test", 1)
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test", 1)

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/L:07\r")
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/L:07\r")
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

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-L:1A\r")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 0)

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/L:1A\r")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 1)
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def DISABLED_test_flipper_single_coil(self):
        # manual flip no hw rule
        self.serial_connections['net2'].expected_commands = {
            "DL:20,89,00,10,0A,FF,00,00,00": "DL:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual enable no hw rule
        self.serial_connections['net2'].expected_commands = {
            "DL:20,C1,00,18,0A,FF,01,00": "DL:P"
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual disable no hw rule
        self.serial_connections['net2'].expected_commands = {
            "TL:20,02": "TL:P"
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # flipper rule enable
        self.serial_connections['net2'].expected_commands = {
            "DL:20,01,01,18,0B,FF,01,00,00": "DL:P",
            "SL:01,01,02,02": "SL:P"
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual flip with hw rule in action
        self.serial_connections['net2'].expected_commands = {
            "DL:20,89,00,10,0A,FF,00,00,00": "DL:P",    # configure and pulse
            "DL:20,01,01,18,0B,FF,01,00,00": "DL:P",    # restore rule
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual flip with hw rule in action without reconfigure (same pulse)
        self.serial_connections['net2'].expected_commands = {
            "TL:20,01": "TL:P",                         # pulse
        }
        self.machine.coils["c_flipper_main"].pulse(11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual enable with hw rule (same pulse)
        self.serial_connections['net2'].expected_commands = {
            "TL:20,03": "TL:P"
        }
        self.machine.coils["c_flipper_main"].enable(pulse_ms=11)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual disable with hw rule
        self.serial_connections['net2'].expected_commands = {
            "TL:20,02": "TL:P",
            "TL:20,00": "TL:P"   # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual enable with hw rule (different pulse)
        self.serial_connections['net2'].expected_commands = {
            "DL:20,C1,00,18,0A,FF,01,00": "DL:P",       # configure pwm + enable
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual disable with hw rule
        self.serial_connections['net2'].expected_commands = {
            "TL:20,02": "TL:P",
            "DL:20,01,01,18,0B,FF,01,00,00": "DL:P",    # configure rules
            "TL:20,00": "TL:P"                          # reenable autofire rule
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # disable rule
        self.serial_connections['net2'].expected_commands = {
            "DL:20,81": "DL:P"
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual flip no hw rule
        self.serial_connections['net2'].expected_commands = {
            "DL:20,89,00,10,0A,FF,00,00,00": "DL:P"
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # manual flip again with cached config
        self.serial_connections['net2'].expected_commands = {
            "TL:20,01": "TL:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def disabled_test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        self.serial_connections['net2'].expected_commands = {
            "DL:20,01,01,18,0A,FF,00,00,00": "DL:P",
            "DL:21,01,01,18,0A,FF,01,00,00": "DL:P",
            "SL:01,01,02,02": "SL:P",
        }
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "DL:20,81": "DL:P",
            "DL:21,81": "DL:P"
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def DISABLED_test_dmd_update(self):

        # test configure
        dmd = self.machine.default_platform.configure_dmd()

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(64 + i % 192)

        frame = bytes(frame)

        # test draw
        self.serial_connections['net2'].expected_commands = {
            b'BM:' + frame: False
        }
        dmd.update(frame)

        self.advance_time_and_run(.1)

        self.assertFalse(self.serial_connections['net2'].expected_commands)

    def DISABLED_test_matrix_lights(self):
        # test enable of matrix light
        self.serial_connections['net2'].expected_commands = {
            "L1:23,FF": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # test enable of matrix light with brightness
        self.serial_connections['net2'].expected_commands = {
            "L1:23,80": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # test disable of matrix light
        self.serial_connections['net2'].expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights["test_pdb_light"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # test disable of matrix light with brightness
        self.serial_connections['net2'].expected_commands = {
            "L1:23,00": "L1:P",
        }
        self.machine.lights["test_pdb_light"].on(brightness=255, fade_ms=100)
        self.advance_time_and_run(.02)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # step 1
        self.serial_connections['net2'].expected_commands = {
            "L1:23,32": "L1:P",
            "L1:23,33": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.serial_connections['net2'].expected_commands))

        # step 2
        self.serial_connections['net2'].expected_commands = {
            "L1:23,65": "L1:P",
            "L1:23,66": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.serial_connections['net2'].expected_commands))

        # step 3
        self.serial_connections['net2'].expected_commands = {
            "L1:23,98": "L1:P",
            "L1:23,99": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.serial_connections['net2'].expected_commands))

        # step 4
        self.serial_connections['net2'].expected_commands = {
            "L1:23,CB": "L1:P",
            "L1:23,CC": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.serial_connections['net2'].expected_commands))

        # step 5
        self.serial_connections['net2'].expected_commands = {
            "L1:23,FE": "L1:P",
            "L1:23,FF": "L1:P",
        }
        self.advance_time_and_run(.02)
        self.assertEqual(1, len(self.serial_connections['net2'].expected_commands))

        # step 6 if step 5 did not send FF
        if "L1:23,FE" not in self.serial_connections['net2'].expected_commands:
            self.serial_connections['net2'].expected_commands = {
                "L1:23,FF": "L1:P",
            }
            self.advance_time_and_run(.02)
            self.assertFalse(self.serial_connections['net2'].expected_commands)

    def DISABLED_test_gi_lights(self):
        # test gi on
        test_gi = self.machine.lights["test_gi"]
        self.serial_connections['net2'].expected_commands = {
            "GI:2A,FF": "GI:P",
        }
        test_gi.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "GI:2A,80": "GI:P",
        }
        test_gi.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        test_gi.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        # test gi off
        self.serial_connections['net2'].expected_commands = {
            "GI:2A,00": "GI:P",
        }
        test_gi.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "GI:2A,F5": "GI:P",
        }
        test_gi.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

        self.serial_connections['net2'].expected_commands = {
            "GI:2A,00": "GI:P",
        }
        test_gi.on(brightness=0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net2'].expected_commands)

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
