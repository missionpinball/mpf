from mpf.core.rgb_color import RGBColor

from mpf.tests.MpfTestCase import MagicMock, test_config, expect_startup_error
from mpf.tests.test_Fast import TestFastBase


class TestFastNano(TestFastBase):
    """FAST Platform class for a networked V1 platform. Tests the NET v1 and RGB processors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net1', 'rgb']

    def get_config_file(self):
        return 'nano.yaml'

    def create_expected_commands(self):

        self.net_cpu.expected_commands = {
            "SN:00": "SN:00,01,1E,1E",
            "SN:01": "SN:01,01,1E,1E",
            "SN:02": "SN:02,01,1E,1E",
            "SN:03": "SN:03,01,1E,1E",
            "SN:04": "SN:04,01,1E,1E",
            "SN:05": "SN:05,01,1E,1E",
            "SN:06": "SN:06,01,1E,1E",
            "SN:07": "SN:07,01,1E,1E",
            "SN:08": "SN:08,01,1E,1E",
            "SN:09": "SN:09,01,1E,1E",
            "SN:0A": "SN:0A,01,1E,1E",
            "SN:0B": "SN:0B,01,1E,1E",
            "SN:0C": "SN:0C,01,1E,1E",
            "SN:0D": "SN:0D,01,1E,1E",
            "SN:0E": "SN:0E,01,1E,1E",
            "SN:0F": "SN:0F,01,1E,1E",
            "SN:10": "SN:10,01,1E,1E",
            "SN:11": "SN:11,01,1E,1E",
            "SN:12": "SN:12,01,1E,1E",
            "SN:13": "SN:13,01,1E,1E",
            "SN:14": "SN:14,01,1E,1E",
            "SN:15": "SN:15,01,1E,1E",
            "SN:16": "SN:16,01,1E,1E",
            "SN:17": "SN:17,01,1E,1E",
            "SN:18": "SN:18,01,1E,1E",
            "SN:19": "SN:19,01,1E,1E",
            "SN:1A": "SN:1A,01,1E,1E",
            "SN:1B": "SN:1B,01,1E,1E",
            "SN:1C": "SN:1C,01,1E,1E",
            "SN:1D": "SN:1D,01,1E,1E",
            "SN:1E": "SN:1E,01,1E,1E",
            "SN:1F": "SN:1F,01,1E,1E",
            "SN:20": "SN:20,01,1E,1E",
            "SN:21": "SN:21,01,1E,1E",
            "SN:22": "SN:22,01,1E,1E",
            "SN:23": "SN:23,01,1E,1E",
            "SN:24": "SN:24,01,1E,1E",
            "SN:25": "SN:25,01,1E,1E",
            "SN:26": "SN:26,01,1E,1E",
            "SN:27": "SN:27,01,1E,1E",
            "SN:28": "SN:28,01,1E,1E",
            "SN:29": "SN:29,01,1E,1E",
            "SN:2A": "SN:2A,01,1E,1E",
            "SN:2B": "SN:2B,01,1E,1E",
            "SN:2C": "SN:2C,01,1E,1E",
            "SN:2D": "SN:2D,01,1E,1E",
            "SN:2E": "SN:2E,01,1E,1E",
            "SN:2F": "SN:2F,01,1E,1E",
            "SN:30": "SN:30,01,1E,1E",
            "SN:31": "SN:31,01,1E,1E",
            "SN:32": "SN:32,01,1E,1E",
            "SN:33": "SN:33,01,1E,1E",
            "SN:34": "SN:34,01,1E,1E",
            "SN:35": "SN:35,01,1E,1E",
            "SN:36": "SN:36,01,1E,1E",
            "SN:37": "SN:37,01,1E,1E",
            "SN:38": "SN:38,01,1E,1E",
            "SN:39": "SN:39,01,1E,1E",
            "SN:3A": "SN:3A,01,1E,1E",
            "SN:3B": "SN:3B,01,1E,1E",
            "SN:3C": "SN:3C,01,1E,1E",
            "SN:3D": "SN:3D,01,1E,1E",
            "SN:3E": "SN:3E,01,1E,1E",
            "SN:3F": "SN:3F,01,1E,1E",
            "SN:40": "SN:40,01,1E,1E",
            "SN:41": "SN:41,01,1E,1E",
            "SN:42": "SN:42,01,1E,1E",
            "SN:43": "SN:43,01,1E,1E",
            "SN:44": "SN:44,01,1E,1E",
            "SN:45": "SN:45,01,1E,1E",
            "SN:46": "SN:46,01,1E,1E",
            "SN:47": "SN:47,01,1E,1E",
            "SN:48": "SN:48,01,1E,1E",
            "SN:49": "SN:49,01,1E,1E",
            "SN:4A": "SN:4A,01,1E,1E",
            "SN:4B": "SN:4B,01,1E,1E",
            "SN:4C": "SN:4C,01,1E,1E",
            "SN:4D": "SN:4D,01,1E,1E",
            "SN:4E": "SN:4E,01,1E,1E",
            "SN:4F": "SN:4F,01,1E,1E",
            "SN:50": "SN:50,01,1E,1E",
            "SN:51": "SN:51,01,1E,1E",
            "SN:52": "SN:52,01,1E,1E",
            "SN:53": "SN:53,01,1E,1E",
            "SN:54": "SN:54,01,1E,1E",
            "SN:55": "SN:55,01,1E,1E",
            "SN:56": "SN:56,01,1E,1E",
            "SN:57": "SN:57,01,1E,1E",
            "SN:58": "SN:58,01,1E,1E",
            "SN:59": "SN:59,01,1E,1E",
            "SN:5A": "SN:5A,01,1E,1E",
            "SN:5B": "SN:5B,01,1E,1E",
            "SN:5C": "SN:5C,01,1E,1E",
            "SN:5D": "SN:5D,01,1E,1E",
            "SN:5E": "SN:5E,01,1E,1E",
            "SN:5F": "SN:5F,01,1E,1E",
            "SN:60": "SN:60,01,1E,1E",
            "SN:61": "SN:61,01,1E,1E",
            "SN:62": "SN:62,01,1E,1E",
            "SN:63": "SN:63,01,1E,1E",
            "SN:64": "SN:64,01,1E,1E",
            "SN:65": "SN:65,01,1E,1E",
            "SN:66": "SN:66,01,1E,1E",
            "SN:67": "SN:67,01,1E,1E",
            "SN:68": "SN:68,01,1E,1E",
            "SN:69": "SN:69,01,1E,1E",
            "SN:6A": "SN:6A,01,1E,1E",
            "SN:6B": "SN:6B,01,1E,1E",

            # Initial driver responses before they're configured:
            "DN:00": "DN:00,00,00,00,00,00,00,00,00",
            "DN:01": "DN:01,00,00,00,00,00,00,00,00",
            "DN:02": "DN:02,00,00,00,00,00,00,00,00",
            "DN:03": "DN:03,00,00,00,00,00,00,00,00",
            "DN:04": "DN:04,00,00,00,00,00,00,00,00",
            "DN:05": "DN:05,00,00,00,00,00,00,00,00",
            "DN:06": "DN:06,00,00,00,00,00,00,00,00",
            "DN:07": "DN:07,00,00,00,00,00,00,00,00",
            "DN:08": "DN:08,00,00,00,00,00,00,00,00",
            "DN:09": "DN:09,00,00,00,00,00,00,00,00",
            "DN:0A": "DN:0A,00,00,00,00,00,00,00,00",
            "DN:0B": "DN:0B,00,00,00,00,00,00,00,00",
            "DN:0C": "DN:0C,00,00,00,00,00,00,00,00",
            "DN:0D": "DN:0D,00,00,00,00,00,00,00,00",
            "DN:0E": "DN:0E,00,00,00,00,00,00,00,00",
            "DN:0F": "DN:0F,00,00,00,00,00,00,00,00",
            "DN:10": "DN:10,00,00,00,00,00,00,00,00",
            "DN:11": "DN:11,00,00,00,00,00,00,00,00",
            "DN:12": "DN:12,00,00,00,00,00,00,00,00",
            "DN:13": "DN:13,00,00,00,00,00,00,00,00",
            "DN:14": "DN:14,00,00,00,00,00,00,00,00",
            "DN:15": "DN:15,00,00,00,00,00,00,00,00",
            "DN:16": "DN:16,00,00,00,00,00,00,00,00",
            "DN:17": "DN:17,00,00,00,00,00,00,00,00",
            "DN:18": "DN:18,00,00,00,00,00,00,00,00",
            "DN:19": "DN:19,00,00,00,00,00,00,00,00",
            "DN:1A": "DN:1A,00,00,00,00,00,00,00,00",
            "DN:1B": "DN:1B,00,00,00,00,00,00,00,00",
            "DN:1C": "DN:1C,00,00,00,00,00,00,00,00",
            "DN:1D": "DN:1D,00,00,00,00,00,00,00,00",
            "DN:1E": "DN:1E,00,00,00,00,00,00,00,00",
            "DN:1F": "DN:1F,00,00,00,00,00,00,00,00",
            "DN:20": "DN:20,00,00,00,00,00,00,00,00",
            "DN:21": "DN:21,00,00,00,00,00,00,00,00",
            "DN:22": "DN:22,00,00,00,00,00,00,00,00",
            "DN:23": "DN:23,00,00,00,00,00,00,00,00",
            "DN:24": "DN:24,00,00,00,00,00,00,00,00",
            "DN:25": "DN:25,00,00,00,00,00,00,00,00",
            "DN:26": "DN:26,00,00,00,00,00,00,00,00",
            "DN:27": "DN:27,00,00,00,00,00,00,00,00",
            "DN:28": "DN:28,00,00,00,00,00,00,00,00",
            "DN:29": "DN:29,00,00,00,00,00,00,00,00",
            "DN:2A": "DN:2A,00,00,00,00,00,00,00,00",
            "DN:2B": "DN:2B,00,00,00,00,00,00,00,00",
            "DN:2C": "DN:2C,00,00,00,00,00,00,00,00",
            "DN:2D": "DN:2D,00,00,00,00,00,00,00,00",
            "DN:2E": "DN:2E,00,00,00,00,00,00,00,00",
            "DN:2F": "DN:2F,00,00,00,00,00,00,00,00",

            'NN:00': 'NN:00,FP-I/O-3208-2   ,01.05,08,20,04,06,00,00,00,00',
            'NN:01': 'NN:01,FP-I/O-0804-1   ,01.05,04,08,04,06,00,00,00,00',
            'NN:02': 'NN:02,FP-I/O-1616-2   ,01.05,10,10,04,06,00,00,00,00',
            'NN:03': 'NN:03,FP-I/O-1616-2   ,01.05,10,10,04,06,00,00,00,00',

            # Initialization commands, also tests all the various switch config options
            "SN:00,00,00,00": "SN:P",
            "SN:01,01,04,04": "SN:P",
            "SN:02,01,04,04": "SN:P",
            "SN:03,01,04,04": "SN:P",
            "SN:04,00,00,00": "SN:P",
            "SN:05,00,00,00": "SN:P",
            "SN:06,00,00,00": "SN:P",
            "SN:07,01,05,1A": "SN:P",
            "SN:08,00,00,00": "SN:P",
            "SN:09,00,00,00": "SN:P",
            "SN:0A,00,00,00": "SN:P",
            "SN:0B,01,04,04": "SN:P",
            "SN:0C,01,04,04": "SN:P",
            "SN:0D,00,00,00": "SN:P",
            "SN:0E,00,00,00": "SN:P",
            "SN:0F,00,00,00": "SN:P",
            "SN:10,00,00,00": "SN:P",
            "SN:11,00,00,00": "SN:P",
            "SN:12,00,00,00": "SN:P",
            "SN:13,00,00,00": "SN:P",
            "SN:14,00,00,00": "SN:P",
            "SN:15,00,00,00": "SN:P",
            "SN:16,01,04,04": "SN:P",
            "SN:17,00,00,00": "SN:P",
            "SN:18,00,00,00": "SN:P",
            "SN:19,00,00,00": "SN:P",
            "SN:1A,02,04,04": "SN:P",
            "SN:1B,00,00,00": "SN:P",
            "SN:1C,00,00,00": "SN:P",
            "SN:1D,00,00,00": "SN:P",
            "SN:1E,00,00,00": "SN:P",
            "SN:1F,00,00,00": "SN:P",
            "SN:20,00,00,00": "SN:P",
            "SN:21,00,00,00": "SN:P",
            "SN:22,00,00,00": "SN:P",
            "SN:23,00,00,00": "SN:P",
            "SN:24,00,00,00": "SN:P",
            "SN:25,00,00,00": "SN:P",
            "SN:26,00,00,00": "SN:P",
            "SN:27,00,00,00": "SN:P",
            "SN:28,00,00,00": "SN:P",
            "SN:29,00,00,00": "SN:P",
            "SN:2A,00,00,00": "SN:P",
            "SN:2B,00,00,00": "SN:P",
            "SN:2C,00,00,00": "SN:P",
            "SN:2D,00,00,00": "SN:P",
            "SN:2E,00,00,00": "SN:P",
            "SN:2F,00,00,00": "SN:P",
            "SN:30,00,00,00": "SN:P",
            "SN:31,00,00,00": "SN:P",
            "SN:32,00,00,00": "SN:P",
            "SN:33,00,00,00": "SN:P",
            "SN:34,00,00,00": "SN:P",
            "SN:35,00,00,00": "SN:P",
            "SN:36,00,00,00": "SN:P",
            "SN:37,00,00,00": "SN:P",
            "SN:38,00,00,00": "SN:P",
            "SN:39,01,04,04": "SN:P",
            "SN:3A,00,00,00": "SN:P",
            "SN:3B,00,00,00": "SN:P",
            "SN:3C,00,00,00": "SN:P",
            "SN:3D,00,00,00": "SN:P",
            "SN:3E,00,00,00": "SN:P",
            "SN:3F,00,00,00": "SN:P",
            "SN:40,00,00,00": "SN:P",
            "SN:41,00,00,00": "SN:P",
            "SN:42,00,00,00": "SN:P",
            "SN:43,00,00,00": "SN:P",
            "SN:44,00,00,00": "SN:P",
            "SN:45,00,00,00": "SN:P",
            "SN:46,00,00,00": "SN:P",
            "SN:47,00,00,00": "SN:P",
            "SN:48,00,00,00": "SN:P",
            "SN:49,00,00,00": "SN:P",
            "SN:4A,00,00,00": "SN:P",
            "SN:4B,00,00,00": "SN:P",
            "SN:4C,00,00,00": "SN:P",
            "SN:4D,00,00,00": "SN:P",
            "SN:4E,00,00,00": "SN:P",
            "SN:4F,00,00,00": "SN:P",
            "SN:50,00,00,00": "SN:P",
            "SN:51,00,00,00": "SN:P",
            "SN:52,00,00,00": "SN:P",
            "SN:53,00,00,00": "SN:P",
            "SN:54,00,00,00": "SN:P",
            "SN:55,00,00,00": "SN:P",
            "SN:56,00,00,00": "SN:P",
            "SN:57,00,00,00": "SN:P",
            "SN:58,00,00,00": "SN:P",
            "SN:59,00,00,00": "SN:P",
            "SN:5A,00,00,00": "SN:P",
            "SN:5B,00,00,00": "SN:P",
            "SN:5C,00,00,00": "SN:P",
            "SN:5D,00,00,00": "SN:P",
            "SN:5E,00,00,00": "SN:P",
            "SN:5F,00,00,00": "SN:P",
            "SN:60,00,00,00": "SN:P",
            "SN:61,00,00,00": "SN:P",
            "SN:62,00,00,00": "SN:P",
            "SN:63,00,00,00": "SN:P",
            "SN:64,00,00,00": "SN:P",
            "SN:65,00,00,00": "SN:P",
            "SN:66,00,00,00": "SN:P",
            "SN:67,00,00,00": "SN:P",
            "SN:68,00,00,00": "SN:P",
            "SN:69,00,00,00": "SN:P",
            "SN:6A,00,00,00": "SN:P",
            "SN:6B,00,00,00": "SN:P",

            # Drivers with configs, tests config options
            "DN:01,81,00,10,FF,FF,00,FF,00": "DN:P",  # initial digital output config, will be updated later
            "DN:04,81,00,10,17,FF,00,00,1B": "DN:P",
            "DN:06,81,00,10,17,FF,00,FF,00": "DN:P",
            "DN:07,81,00,10,0A,FF,00,00,00": "DN:P",
            "DN:11,81,00,10,0A,AA,00,92,00": "DN:P",
            "DN:12,81,00,70,0A,FF,14,FF,00": "DN:P",
            "DN:13,81,00,10,0A,FF,00,88,00": "DN:P",
            "DN:16,81,00,10,14,FF,00,88,00": "DN:P",
            "DN:17,81,00,10,14,FF,00,88,00": "DN:P",
            "DN:20,81,00,10,0A,FF,00,01,00": "DN:P",
            "DN:21,81,00,10,0A,FF,00,01,00": "DN:P",

            # Digital output which after the initial pass
            "DN:01,C1,00,18,00,FF,FF,00,00": "DN:P",
            }

    def setUp(self):
        super().setUp()
        if not self.startup_error:
            self.advance_time_and_run()
            self.assertFalse(self.net_cpu.expected_commands)
            self.assertFalse(self.rgb_cpu.expected_commands)

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

        # test hardware scan
        info_str = (
            'NET: FP-CPU-002-2 v01.05\n'
            'RGB: FP-CPU-002-2 v01.00\n'
            '\n'
            'I/O Boards:\n'
            'Board 0 - Model: FP-I/O-3208, Firmware: 01.05, Switches: 32, Drivers: 8\n'
            'Board 1 - Model: FP-I/O-0804, Firmware: 01.05, Switches: 8, Drivers: 4\n'
            'Board 2 - Model: FP-I/O-1616, Firmware: 01.05, Switches: 16, Drivers: 16\n'
            'Board 3 - Model: FP-I/O-1616, Firmware: 01.05, Switches: 16, Drivers: 16\n'
            )

        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_pulse(self):
        self.net_cpu.expected_commands = {
            "TN:04,01": "TN:P"
        }
        # pulse coil 4
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_long_pulse(self):
        # driver is configured for mode 70, so this should be a regular trigger
        self.net_cpu.expected_commands = {
            "TN:12,01": "TN:P"
        }
        self.machine.coils["c_long_pulse"].pulse()
        self.advance_time_and_run(.1)
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
            "DN:06,C1,00,18,17,FF,FF,00,00": "DN:P"
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_pwm_ssm(self):
        self.net_cpu.expected_commands = {
            "DN:13,C1,00,18,0A,FF,88,00,00": "DN:P"
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
        self._test_hw_rule_pulse_pwm()
        self._test_hw_rule_pulse_inverted_switch()
        self._test_hw_rule_same_board()

    def _test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.flippers["f_test_single"].config['main_coil_overwrite']['hold_power'] = 1.0
            self.machine.flippers["f_test_single"].enable()

        self.machine.flippers["f_test_single"].config['main_coil_overwrite']['hold_power'] = None

    def _test_two_rules_one_switch(self):
        self.net_cpu.expected_commands = {
            "TN:04,00,03": "TN:P",
            "TN:06,00,03": "TN:P"
        }
        self.post_event("ac_same_switch")
        self.hit_and_release_switch("s_flipper")
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse(self):
        self.net_cpu.expected_commands = {
            "TN:07,00,16": "TN:P",  # hw rule
        }
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "TN:07,02": "TN:P"
        }
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_pwm(self):
        self.net_cpu.expected_commands = {
            "TN:11,01": "TN:P"
        }
        self.machine.coils["c_pulse_pwm_mask"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "DN:11,C1,00,18,0A,AA,92,00,00": "DN:P"
        }
        self.machine.coils["c_pulse_pwm_mask"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_pulse_inverted_switch(self):
        self.net_cpu.expected_commands = {
            "DN:07,11,1A,10,0A,FF,00,00,00": "DN:P",
        }
        self.machine.autofire_coils["ac_inverted_switch"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

    def _test_hw_rule_same_board(self):
        self.net_cpu.expected_commands = {
            "TN:21,00,07": "DN:P"
        }
        # coil and switch are on different boards but first 8 switches always work
        self.machine.autofire_coils["ac_different_boards"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # switch and coil on board 3. should work
        self.net_cpu.expected_commands = {
            "TN:21,00,39": "DN:P",
        }
        self.machine.autofire_coils["ac_board_3"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # coil and switch are on different boards
        with self.assertRaises(AssertionError):
            self.machine.autofire_coils["ac_broken_combination"].enable()
            self.advance_time_and_run(.1)

    def _switch_hit_cb(self, **kwargs):
        self.switch_hit = True

    def test_switches(self):
        self._test_switch_changes()
        self._test_switch_changes_nc()

    def _test_switch_changes(self):
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_flipper_eos", 0)

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
        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test_nc", 0)
        self.assertFalse(self.switch_hit)

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 0)

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-N:1A\r")
        self.advance_time_and_run(1)
        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_test_nc", 1)

        self.switch_hit = False
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/N:1A\r")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 0)
        self.assertFalse(self.switch_hit)
        self.switch_hit = False

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "TN:20,01": "TN:P",
        }
        self.machine.coils["c_flipper_main"].pulse()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,C1,00,18,0A,FF,01,00,00": "DN:P"
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
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip with hw rule in action
        # TODO I think this is wrong? Check with Dave
        self.net_cpu.expected_commands = {
            "DN:20,09,01,18,0A,FF,01,00,00": "DN:P",    # manual pulse 10ms, trigger 09 = one_shot + driver enable
            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",    # restore autofire rule
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
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual enable with hw rule (different pulse)
        self.net_cpu.expected_commands = {
            "DN:20,C1,01,18,0A,FF,01,00,00": "DN:P",       # configure pwm + enable
        }
        self.machine.coils["c_flipper_main"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual disable with hw rule
        self.net_cpu.expected_commands = {

            "DN:20,01,01,18,0B,FF,01,00,00": "DN:P",    # configure rules
        }
        self.machine.coils["c_flipper_main"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # disable rule
        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P"                          # disable autofire rule
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        # manual flip no hw rule
        self.net_cpu.expected_commands = {
            "DN:20,89,01,18,0A,FF,01,00,00": "DN:P"  # TODO verify this
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
        }
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu.expected_commands)

        self.net_cpu.expected_commands = {
            "TN:20,02": "TN:P",
            "TN:21,02": "TN:P"
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

    # TODO figure out what to do here
    def test_bootloader_crash_ignored(self):
        # Test that RGB processor bootloader msgs can be ignored
        self.machine.default_platform.config['ignore_reboot'] = True
        self.mock_event('fast_rgb_rebooted')
        self.machine.stop = MagicMock()
        self.machine.default_platform.serial_connections['rgb'].parse_incoming_raw_bytes(b"!B:00\r")
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.stop.called)
        self.assertEventCalled('fast_rgb_rebooted')

    def test_leds(self):

        # Verify the old style number works
        self.assertEqual("00-0", self.machine.lights['old_style_number'].hw_drivers['red'][0].number)

        self.advance_time_and_run()
        device = self.machine.lights["test_led"]   # 0x56
        device2 = self.machine.lights["test_led2"]  #0x57
        self.assertEqual("000000", self.rgb_cpu.leds['56'])
        self.assertEqual("000000", self.rgb_cpu.leds['57'])
        # test led on
        device.on()
        self.advance_time_and_run(1)
        self.assertEqual("FFFFFF", self.rgb_cpu.leds['56'])
        self.assertEqual("000000", self.rgb_cpu.leds['57'])

        device.color("112233")
        device2.color("001122")
        self.advance_time_and_run(1)
        self.assertEqual("112233", self.rgb_cpu.leds['56'])
        self.assertEqual("110022", self.rgb_cpu.leds['57'])  # GRB so ensure it's not 001122

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['56'])
        self.assertEqual("110022", self.rgb_cpu.leds['57'])  # GRB so ensure it's not 001122

        # test led color
        device2.color(RGBColor((2, 23, 42)))  #02172A
        self.advance_time_and_run(1)
        self.assertEqual("17022A", self.rgb_cpu.leds['57'])  # GRB so ensure it's not 02172A

        # test led off
        device2.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", self.rgb_cpu.leds['57'])

        self.advance_time_and_run(.02)

        # fade led over 100ms
        device2.color(RGBColor((100, 100, 100)), fade_ms=100)
        self.advance_time_and_run(.03)
        self.assertTrue(10 < int(self.rgb_cpu.leds['57'][0:2], 16) < 40)
        self.assertTrue(self.rgb_cpu.leds['57'][0:2] == self.rgb_cpu.leds['57'][2:4] == self.rgb_cpu.leds['57'][4:6])
        self.advance_time_and_run(.03)
        self.assertTrue(40 < int(self.rgb_cpu.leds['57'][0:2], 16) < 60)
        self.assertTrue(self.rgb_cpu.leds['57'][0:2] == self.rgb_cpu.leds['57'][2:4] == self.rgb_cpu.leds['57'][4:6])
        self.advance_time_and_run(.03)
        self.assertTrue(60 < int(self.rgb_cpu.leds['57'][0:2], 16) < 90)
        self.assertTrue(self.rgb_cpu.leds['57'][0:2] == self.rgb_cpu.leds['57'][2:4] == self.rgb_cpu.leds['57'][4:6])
        self.advance_time_and_run(2)
        self.assertEqual("646464", self.rgb_cpu.leds['57'])

    # TODO need to go through the entire FAST platform and cleanup config errors and error logging in general
    # @expect_startup_error()
    # @test_config("error_lights.yaml")
    # def test_light_errors(self):
    #     self.assertIsInstance(self.startup_error, ConfigFileError)
    #     self.assertEqual(2, self.startup_error.get_error_no())
    #     self.assertEqual("light.test_led", self.startup_error.get_logger_name())
    #     self.assertIsInstance(self.startup_error.__cause__, ConfigFileError)
    #     self.assertEqual(9, self.startup_error.__cause__.get_error_no())
    #     self.assertEqual("FAST", self.startup_error.__cause__.get_logger_name())
    #     self.assertEqual("Light syntax is number-channel (but was \"3\") for light test_led.",
    #                      self.startup_error.__cause__._message)