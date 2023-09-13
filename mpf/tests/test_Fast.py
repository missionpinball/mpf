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
                self.serial_connections['net2'] = MockFastNetNeuron(self)  # default com3
            elif conn == 'exp':
                self.serial_connections['exp'] = MockFastExp(self)  # default com4
            elif conn == 'rgb':
                self.serial_connections['rgb'] = MockFastRgb(self)  # default com5
            elif conn == 'net1':
                self.serial_connections['net1'] = MockFastNetNano(self)  # default com6
            elif conn == 'seg':
                self.serial_connections['seg'] = MockFastSeg(self)  # default com7
            elif conn == 'dmd':
                self.serial_connections['dmd'] = MockFastDmd(self)  # default com8

    def confirm_commands(self):
        self.advance_time_and_run(.1)
        for conn in self.serial_connections.values():
            self.assertFalse(conn.expected_commands)

    def create_expected_commands(self):
        # These are all the defaults based on the config file for this test.
        # Individual tests can override / add as needed

        self.serial_connections['net2'].expected_commands = {
            'NN:00': 'NN:00,FP-I/O-3208-3   ,01.10,08,20,00,00,00,00,00,00',
            'NN:01': 'NN:01,FP-I/O-0804-3   ,01.10,04,08,00,00,00,00,00,00',
            'NN:02': 'NN:02,FP-I/O-1616-3   ,01.10,10,10,00,00,00,00,00,00',
            'NN:03': 'NN:03,FP-I/O-0024-3   ,01.10,08,18,00,00,00,00,00,00',

            # Initial switch responses before they're configured:
            "SL:00": "SL:00,01,02,04",
            "SL:01": "SL:01,01,02,04",
            "SL:02": "SL:02,01,02,04",
            "SL:03": "SL:03,01,02,04",
            "SL:04": "SL:04,01,02,04",
            "SL:05": "SL:05,01,02,04",
            "SL:06": "SL:06,01,02,04",
            "SL:07": "SL:07,01,02,04",
            "SL:08": "SL:08,01,02,04",
            "SL:09": "SL:09,01,02,04",
            "SL:0A": "SL:0A,01,02,04",
            "SL:0B": "SL:0B,01,02,04",
            "SL:0C": "SL:0C,01,02,04",
            "SL:0D": "SL:0D,01,02,04",
            "SL:0E": "SL:0E,01,02,04",
            "SL:0F": "SL:0F,01,02,04",
            "SL:10": "SL:10,01,02,04",
            "SL:11": "SL:11,01,02,04",
            "SL:12": "SL:12,01,02,04",
            "SL:13": "SL:13,01,02,04",
            "SL:14": "SL:14,01,02,04",
            "SL:15": "SL:15,01,02,04",
            "SL:16": "SL:16,01,02,04",
            "SL:17": "SL:17,01,02,04",
            "SL:18": "SL:18,01,02,04",
            "SL:19": "SL:19,01,02,04",
            "SL:1A": "SL:1A,01,02,04",
            "SL:1B": "SL:1B,01,02,04",
            "SL:1C": "SL:1C,01,02,04",
            "SL:1D": "SL:1D,01,02,04",
            "SL:1E": "SL:1E,01,02,04",
            "SL:1F": "SL:1F,01,02,04",
            "SL:20": "SL:20,01,02,04",
            "SL:21": "SL:21,01,02,04",
            "SL:22": "SL:22,01,02,04",
            "SL:23": "SL:23,01,02,04",
            "SL:24": "SL:24,01,02,04",
            "SL:25": "SL:25,01,02,04",
            "SL:26": "SL:26,01,02,04",
            "SL:27": "SL:27,01,02,04",
            "SL:28": "SL:28,01,02,04",
            "SL:29": "SL:29,01,02,04",
            "SL:2A": "SL:2A,01,02,04",
            "SL:2B": "SL:2B,01,02,04",
            "SL:2C": "SL:2C,01,02,04",
            "SL:2D": "SL:2D,01,02,04",
            "SL:2E": "SL:2E,01,02,04",
            "SL:2F": "SL:2F,01,02,04",
            "SL:30": "SL:30,01,02,04",
            "SL:31": "SL:31,01,02,04",
            "SL:32": "SL:32,01,02,04",
            "SL:33": "SL:33,01,02,04",
            "SL:34": "SL:34,01,02,04",
            "SL:35": "SL:35,01,02,04",
            "SL:36": "SL:36,01,02,04",
            "SL:37": "SL:37,01,02,04",
            "SL:38": "SL:38,01,02,04",
            "SL:39": "SL:39,01,02,04",
            "SL:3A": "SL:3A,01,02,04",
            "SL:3B": "SL:3B,01,02,04",
            "SL:3C": "SL:3C,01,02,04",
            "SL:3D": "SL:3D,01,02,04",
            "SL:3E": "SL:3E,01,02,04",
            "SL:3F": "SL:3F,01,02,04",
            "SL:40": "SL:40,01,02,04",
            "SL:41": "SL:41,01,02,04",
            "SL:42": "SL:42,01,02,04",
            "SL:43": "SL:43,01,02,04",
            "SL:44": "SL:44,01,02,04",
            "SL:45": "SL:45,01,02,04",
            "SL:46": "SL:46,01,02,04",
            "SL:47": "SL:47,01,02,04",
            "SL:48": "SL:48,01,02,04",
            "SL:49": "SL:49,01,02,04",
            "SL:4A": "SL:4A,01,02,04",
            "SL:4B": "SL:4B,01,02,04",
            "SL:4C": "SL:4C,01,02,04",
            "SL:4D": "SL:4D,01,02,04",
            "SL:4E": "SL:4E,01,02,04",
            "SL:4F": "SL:4F,01,02,04",
            "SL:50": "SL:50,01,02,04",
            "SL:51": "SL:51,01,02,04",
            "SL:52": "SL:52,01,02,04",
            "SL:53": "SL:53,01,02,04",
            "SL:54": "SL:54,01,02,04",
            "SL:55": "SL:55,01,02,04",
            "SL:56": "SL:56,01,02,04",
            "SL:57": "SL:57,01,02,04",
            "SL:58": "SL:58,01,02,04",
            "SL:59": "SL:59,01,02,04",
            "SL:5A": "SL:5A,01,02,04",
            "SL:5B": "SL:5B,01,02,04",
            "SL:5C": "SL:5C,01,02,04",
            "SL:5D": "SL:5D,01,02,04",
            "SL:5E": "SL:5E,01,02,04",
            "SL:5F": "SL:5F,01,02,04",
            "SL:60": "SL:60,01,02,04",
            "SL:61": "SL:61,01,02,04",
            "SL:62": "SL:62,01,02,04",
            "SL:63": "SL:63,01,02,04",
            "SL:64": "SL:64,01,02,04",
            "SL:65": "SL:65,01,02,04",
            "SL:66": "SL:66,01,02,04",
            "SL:67": "SL:67,01,02,04",

            # Initial driver responses before they're configured:
            "DL:00": "DL:00,00,00,00,00,00,00,00,00",
            "DL:01": "DL:01,00,00,00,00,00,00,00,00",
            "DL:02": "DL:02,00,00,00,00,00,00,00,00",
            "DL:03": "DL:03,00,00,00,00,00,00,00,00",
            "DL:04": "DL:04,00,00,00,00,00,00,00,00",
            "DL:05": "DL:05,00,00,00,00,00,00,00,00",
            "DL:06": "DL:06,00,00,00,00,00,00,00,00",
            "DL:07": "DL:07,00,00,00,00,00,00,00,00",
            "DL:08": "DL:08,00,00,00,00,00,00,00,00",
            "DL:09": "DL:09,00,00,00,00,00,00,00,00",
            "DL:0A": "DL:0A,00,00,00,00,00,00,00,00",
            "DL:0B": "DL:0B,00,00,00,00,00,00,00,00",
            "DL:0C": "DL:0C,00,00,00,00,00,00,00,00",
            "DL:0D": "DL:0D,00,00,00,00,00,00,00,00",
            "DL:0E": "DL:0E,00,00,00,00,00,00,00,00",
            "DL:0F": "DL:0F,00,00,00,00,00,00,00,00",
            "DL:10": "DL:10,00,00,00,00,00,00,00,00",
            "DL:11": "DL:11,00,00,00,00,00,00,00,00",
            "DL:12": "DL:12,00,00,00,00,00,00,00,00",
            "DL:13": "DL:13,00,00,00,00,00,00,00,00",
            "DL:14": "DL:14,00,00,00,00,00,00,00,00",
            "DL:15": "DL:15,00,00,00,00,00,00,00,00",
            "DL:16": "DL:16,00,00,00,00,00,00,00,00",
            "DL:17": "DL:17,00,00,00,00,00,00,00,00",
            "DL:18": "DL:18,00,00,00,00,00,00,00,00",
            "DL:19": "DL:19,00,00,00,00,00,00,00,00",
            "DL:1A": "DL:1A,00,00,00,00,00,00,00,00",
            "DL:1B": "DL:1B,00,00,00,00,00,00,00,00",
            "DL:1C": "DL:1C,00,00,00,00,00,00,00,00",
            "DL:1D": "DL:1D,00,00,00,00,00,00,00,00",
            "DL:1E": "DL:1E,00,00,00,00,00,00,00,00",
            "DL:1F": "DL:1F,00,00,00,00,00,00,00,00",
            "DL:20": "DL:20,00,00,00,00,00,00,00,00",
            "DL:21": "DL:21,00,00,00,00,00,00,00,00",
            "DL:22": "DL:22,00,00,00,00,00,00,00,00",
            "DL:23": "DL:23,00,00,00,00,00,00,00,00",
            "DL:24": "DL:24,00,00,00,00,00,00,00,00",
            "DL:25": "DL:25,00,00,00,00,00,00,00,00",
            "DL:26": "DL:26,00,00,00,00,00,00,00,00",
            "DL:27": "DL:27,00,00,00,00,00,00,00,00",
            "DL:28": "DL:28,00,00,00,00,00,00,00,00",
            "DL:29": "DL:29,00,00,00,00,00,00,00,00",
            "DL:2A": "DL:2A,00,00,00,00,00,00,00,00",
            "DL:2B": "DL:2B,00,00,00,00,00,00,00,00",
            "DL:2C": "DL:2C,00,00,00,00,00,00,00,00",
            "DL:2D": "DL:2D,00,00,00,00,00,00,00,00",
            "DL:2E": "DL:2E,00,00,00,00,00,00,00,00",
            "DL:2F": "DL:2F,00,00,00,00,00,00,00,00",

            # All 104 switches are initialized, even if they do not exist in the MPF config
            "SL:00,01,04,04": "SL:P",
            "SL:01,01,04,04": "SL:P",
            "SL:02,01,04,04": "SL:P",
            "SL:03,02,04,04": "SL:P",
            "SL:04,01,04,04": "SL:P",
            "SL:05,02,04,04": "SL:P",
            "SL:06,01,04,04": "SL:P",
            "SL:07,01,02,02": "SL:P",
            "SL:08,01,04,04": "SL:P",
            "SL:09,01,05,1A": "SL:P",
            "SL:0A,00,00,00": "SL:P",
            "SL:0B,00,00,00": "SL:P",
            "SL:0C,00,00,00": "SL:P",
            "SL:0D,00,00,00": "SL:P",
            "SL:0E,00,00,00": "SL:P",
            "SL:0F,00,00,00": "SL:P",
            "SL:10,00,00,00": "SL:P",
            "SL:11,00,00,00": "SL:P",
            "SL:12,00,00,00": "SL:P",
            "SL:13,00,00,00": "SL:P",
            "SL:14,00,00,00": "SL:P",
            "SL:15,00,00,00": "SL:P",
            "SL:16,00,00,00": "SL:P",
            "SL:17,00,00,00": "SL:P",
            "SL:18,00,00,00": "SL:P",
            "SL:19,00,00,00": "SL:P",
            "SL:1A,00,00,00": "SL:P",
            "SL:1B,00,00,00": "SL:P",
            "SL:1C,00,00,00": "SL:P",
            "SL:1D,00,00,00": "SL:P",
            "SL:1E,00,00,00": "SL:P",
            "SL:1F,00,00,00": "SL:P",
            "SL:20,00,00,00": "SL:P",
            "SL:21,00,00,00": "SL:P",
            "SL:22,00,00,00": "SL:P",
            "SL:23,00,00,00": "SL:P",
            "SL:24,00,00,00": "SL:P",
            "SL:25,00,00,00": "SL:P",
            "SL:26,00,00,00": "SL:P",
            "SL:27,00,00,00": "SL:P",
            "SL:28,01,04,04": "SL:P",
            "SL:29,00,00,00": "SL:P",
            "SL:2A,00,00,00": "SL:P",
            "SL:2B,00,00,00": "SL:P",
            "SL:2C,00,00,00": "SL:P",
            "SL:2D,00,00,00": "SL:P",
            "SL:2E,00,00,00": "SL:P",
            "SL:2F,00,00,00": "SL:P",
            "SL:30,00,00,00": "SL:P",
            "SL:31,00,00,00": "SL:P",
            "SL:32,00,00,00": "SL:P",
            "SL:33,00,00,00": "SL:P",
            "SL:34,00,00,00": "SL:P",
            "SL:35,00,00,00": "SL:P",
            "SL:36,00,00,00": "SL:P",
            "SL:37,00,00,00": "SL:P",
            "SL:38,01,04,04": "SL:P",
            "SL:39,00,00,00": "SL:P",
            "SL:3A,00,00,00": "SL:P",
            "SL:3B,00,00,00": "SL:P",
            "SL:3C,00,00,00": "SL:P",
            "SL:3D,00,00,00": "SL:P",
            "SL:3E,00,00,00": "SL:P",
            "SL:3F,00,00,00": "SL:P",
            "SL:40,00,00,00": "SL:P",
            "SL:41,00,00,00": "SL:P",
            "SL:42,00,00,00": "SL:P",
            "SL:43,00,00,00": "SL:P",
            "SL:44,00,00,00": "SL:P",
            "SL:45,00,00,00": "SL:P",
            "SL:46,00,00,00": "SL:P",
            "SL:47,00,00,00": "SL:P",
            "SL:48,00,00,00": "SL:P",
            "SL:49,00,00,00": "SL:P",
            "SL:4A,00,00,00": "SL:P",
            "SL:4B,00,00,00": "SL:P",
            "SL:4C,00,00,00": "SL:P",
            "SL:4D,00,00,00": "SL:P",
            "SL:4E,00,00,00": "SL:P",
            "SL:4F,00,00,00": "SL:P",
            "SL:50,00,00,00": "SL:P",
            "SL:51,00,00,00": "SL:P",
            "SL:52,00,00,00": "SL:P",
            "SL:53,00,00,00": "SL:P",
            "SL:54,00,00,00": "SL:P",
            "SL:55,00,00,00": "SL:P",
            "SL:56,00,00,00": "SL:P",
            "SL:57,00,00,00": "SL:P",
            "SL:58,00,00,00": "SL:P",
            "SL:59,00,00,00": "SL:P",
            "SL:5A,00,00,00": "SL:P",
            "SL:5B,00,00,00": "SL:P",
            "SL:5C,00,00,00": "SL:P",
            "SL:5D,00,00,00": "SL:P",
            "SL:5E,00,00,00": "SL:P",
            "SL:5F,00,00,00": "SL:P",
            "SL:60,00,00,00": "SL:P",
            "SL:61,00,00,00": "SL:P",
            "SL:62,00,00,00": "SL:P",
            "SL:63,00,00,00": "SL:P",
            "SL:64,00,00,00": "SL:P",
            "SL:65,00,00,00": "SL:P",
            "SL:66,00,00,00": "SL:P",
            "SL:67,00,00,00": "SL:P",

            # All 48 drivers are initialized, even if they do not exist in the MPF config
            "DL:00,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:01,81,00,10,0A,FF,00,FF,00": "DL:P",
            "DL:02,81,00,10,17,AA,00,00,00": "DL:P",
            "DL:05,81,00,10,0A,FF,00,00,1B": "DL:P",
            "DL:06,81,00,70,0A,FF,14,EE,00": "DL:P",
            "DL:07,81,00,10,0A,FF,00,88,00": "DL:P",
            "DL:08,81,00,70,0A,FF,C8,EE,00": "DL:P",
            "DL:0A,81,00,10,18,FE,14,AA,00": "DL:P",
            "DL:0B,81,00,10,14,AA,14,AA,00": "DL:P",
            "DL:0D,81,00,10,0A,FF,00,01,00": "DL:P",
            "DL:0E,81,00,10,0A,FF,00,01,00": "DL:P",
            "DL:0F,81,00,10,0E,FF,00,01,00": "DL:P",
            "DL:10,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:11,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:12,81,00,10,0F,FF,00,00,00": "DL:P",
            "DL:13,81,00,10,0A,FF,00,00,00": "DL:P",
            }

        # self.serial_connections['net2'].expected_commands['SL:L'] = (
        #     'SL:68\r'
        #     'SL:00,02,01,02\r'
        #     'SL:01,01,03,04\r'
        #     'SL:02,01,02,14\r'
        #     'SL:03,01,02,14\r'
        #     'SL:04,01,02,14\r'
        #     'SL:05,01,02,14\r'
        #     'SL:06,01,02,14\r'
        #     'SL:07,01,02,14\r'
        #     'SL:08,01,02,14\r'
        #     'SL:09,01,02,14\r'
        #     'SL:0A,01,02,14\r'
        #     'SL:0B,01,02,14\r'
        #     'SL:0C,01,02,14\r'
        #     'SL:0D,01,02,14\r'
        #     'SL:0E,01,02,14\r'
        #     'SL:0F,01,02,14\r'
        #     'SL:10,01,02,14\r'
        #     'SL:11,01,02,14\r'
        #     'SL:12,01,02,14\r'
        #     'SL:13,01,02,14\r'
        #     'SL:14,01,02,14\r'
        #     'SL:15,01,02,14\r'
        #     'SL:16,01,02,14\r'
        #     'SL:17,01,02,14\r'
        #     'SL:18,01,02,14\r'
        #     'SL:19,01,02,14\r'
        #     'SL:1A,01,02,14\r'
        #     'SL:1B,01,02,14\r'
        #     'SL:1C,01,02,14\r'
        #     'SL:1D,01,02,14\r'
        #     'SL:1E,01,02,14\r'
        #     'SL:1F,01,02,14\r'
        #     'SL:20,01,02,14\r'
        #     'SL:21,01,02,14\r'
        #     'SL:22,01,02,14\r'
        #     'SL:23,01,02,14\r'
        #     'SL:24,01,02,14\r'
        #     'SL:25,01,02,14\r'
        #     'SL:26,01,02,14\r'
        #     'SL:27,01,02,14\r'
        #     'SL:28,01,02,14\r'
        #     'SL:29,01,02,14\r'
        #     'SL:2A,01,02,14\r'
        #     'SL:2B,01,02,14\r'
        #     'SL:2C,01,02,14\r'
        #     'SL:2D,01,02,14\r'
        #     'SL:2E,01,02,14\r'
        #     'SL:2F,01,02,14\r'
        #     'SL:30,01,02,14\r'
        #     'SL:31,01,02,14\r'
        #     'SL:32,01,02,14\r'
        #     'SL:33,01,02,14\r'
        #     'SL:34,01,02,14\r'
        #     'SL:35,01,02,14\r'
        #     'SL:36,01,02,14\r'
        #     'SL:37,01,02,14\r'
        #     'SL:38,01,02,14\r'
        #     'SL:39,01,02,14\r'
        #     'SL:3A,01,02,14\r'
        #     'SL:3B,01,02,14\r'
        #     'SL:3C,01,02,14\r'
        #     'SL:3D,01,02,14\r'
        #     'SL:3E,01,02,14\r'
        #     'SL:3F,01,02,14\r'
        #     'SL:40,01,02,14\r'
        #     'SL:41,01,02,14\r'
        #     'SL:42,01,02,14\r'
        #     'SL:43,01,02,14\r'
        #     'SL:44,01,02,14\r'
        #     'SL:45,01,02,14\r'
        #     'SL:46,01,02,14\r'
        #     'SL:47,01,02,14\r'
        #     'SL:48,01,02,14\r'
        #     'SL:49,01,02,14\r'
        #     'SL:4A,01,02,14\r'
        #     'SL:4B,01,02,14\r'
        #     'SL:4C,01,02,14\r'
        #     'SL:4D,01,02,14\r'
        #     'SL:4E,01,02,14\r'
        #     'SL:4F,01,02,14\r'
        #     'SL:50,01,02,14\r'
        #     'SL:51,01,02,14\r'
        #     'SL:52,01,02,14\r'
        #     'SL:53,01,02,14\r'
        #     'SL:54,01,02,14\r'
        #     'SL:55,01,02,14\r'
        #     'SL:56,01,02,14\r'
        #     'SL:57,01,02,14\r'
        #     'SL:58,01,02,14\r'
        #     'SL:59,01,02,14\r'
        #     'SL:5A,01,02,14\r'
        #     'SL:5B,01,02,14\r'
        #     'SL:5C,01,02,14\r'
        #     'SL:5D,01,02,14\r'
        #     'SL:5E,01,02,14\r'
        #     'SL:5F,01,02,14\r'
        #     'SL:60,01,02,14\r'
        #     'SL:61,01,02,14\r'
        #     'SL:62,01,02,14\r'
        #     'SL:63,01,02,14\r'
        #     'SL:64,01,02,14\r'
        #     'SL:65,01,02,14\r'
        #     'SL:66,01,02,14\r'
        #     'SL:67,01,02,14\r'
        #     )

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
            self.assertEqual(4, len(self.machine.default_platform.io_boards))
            self.assertEqual(32, self.machine.default_platform.io_boards[0].switch_count)
            self.assertEqual(8, self.machine.default_platform.io_boards[0].driver_count)
            self.assertEqual(8, self.machine.default_platform.io_boards[1].switch_count)
            self.assertEqual(4, self.machine.default_platform.io_boards[1].driver_count)
            self.assertEqual(16, self.machine.default_platform.io_boards[2].switch_count)
            self.assertEqual(16, self.machine.default_platform.io_boards[2].driver_count)
            self.assertEqual(24, self.machine.default_platform.io_boards[3].switch_count)
            self.assertEqual(8, self.machine.default_platform.io_boards[3].driver_count)

            for conn in self.serial_connections.values():
                self.assertFalse(conn.expected_commands)

        # If a test is testing a bad config file and causes a startup exception,
        # the machine will shut down. Safety check before we add futures to the loop.
        if not self.machine.is_shutting_down:
            self.advance_time_and_run(1)

    def test_coils(self):
        # The default expected commands will verify all the coils are configured properly.
        # We just need to ensure things get enabled properly.
        self.confirm_commands()

        self._test_pulse()
        self._test_long_pulse()
        self._test_timed_enable()
        self._test_default_timed_enable()
        self._test_enable_exception()
        self._test_allow_enable()
        # self._test_pwm_ssm()

        # test hardware scan
        info_str = (
            'NET: FP-CPU-2000 v02.13\n'
            '\n'
            'I/O Boards:\n'
            'Board 0 - Model: FP-I/O-3208, Firmware: 01.10, Switches: 32, Drivers: 8\n'
            'Board 1 - Model: FP-I/O-0804, Firmware: 01.10, Switches: 8, Drivers: 4\n'
            'Board 2 - Model: FP-I/O-1616, Firmware: 01.10, Switches: 16, Drivers: 16\n'
            'Board 3 - Model: FP-I/O-0024, Firmware: 01.10, Switches: 24, Drivers: 8\n'
            )

        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_pulse(self):

        coil = self.machine.coils["c_baseline"]

        # pulse based on its initial config
        self.serial_connections['net2'].expected_commands = {"TL:00,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

        # pulse with a non-standard pulse_ms, trigger 89 also pulses now
        self.serial_connections['net2'].expected_commands = {'DL:00,89,00,10,32,FF,00,00,00': 'DL:P'}
        coil.pulse(50)
        self.confirm_commands()

        # Pulse again and it should just use a TL since the coil is already configured
        self.serial_connections['net2'].expected_commands = {"TL:00,01": "TL:P"}
        coil.pulse(50)
        self.confirm_commands()

        # Pulse default and it should reconfigure to default
        self.serial_connections['net2'].expected_commands = {'DL:00,89,00,10,0A,FF,00,00,00': 'DL:P'}
        coil.pulse()
        self.confirm_commands()

        # pulse with non-standard ms and power
        self.serial_connections['net2'].expected_commands = {'DL:00,89,00,10,64,92,00,00,00': 'DL:P'}
        coil.pulse(100, 0.375)
        self.confirm_commands()

        # Do that same pulse again and it should just use a TL since the coil is already configured
        self.serial_connections['net2'].expected_commands = {"TL:00,01": "TL:P"}
        coil.pulse(100, 0.375)
        self.confirm_commands()

    def _test_long_pulse(self):

        coil = self.machine.coils["c_long_pwm2"]

        # pulse based on its initial config
        self.serial_connections['net2'].expected_commands = {"TL:06,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

        self.advance_time_and_run(21)
        # pulse it again, but disable it partway through

        self.serial_connections['net2'].expected_commands = {"TL:06,01": "TL:P",
                                                             "TL:06,02": "TL:P",
                                                            }

        coil.pulse()
        self.advance_time_and_run(1)
        coil.disable()
        self.confirm_commands()

    def _test_timed_enable(self):

        coil = self.machine.coils["c_long_pwm2"]  # DL:06,81,00,70,0A,FF,14,EE,00

        # timed_enable based on its current config
        self.serial_connections['net2'].expected_commands = {"TL:06,01": "TL:P"}
        coil.timed_enable()
        self.confirm_commands()

        self.serial_connections['net2'].expected_commands = {"DL:06,89,00,70,0F,FF,0A,88,00": "TL:P"}
        coil.timed_enable(1000, 0.25, 15, 1.0)
        self.confirm_commands()

    def _test_default_timed_enable(self):
        # test that a regular pulse() command will use the long pulse config
        coil = self.machine.coils["c_longer_pwm2"]  # DL:08,81,00,70,0A,FF,C8,EE,00

        # timed_enable based on its current config
        self.serial_connections['net2'].expected_commands = {"TL:08,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils["c_baseline"].enable()
            self.advance_time_and_run(.1)

    def _test_allow_enable(self):
        self.serial_connections['net2'].expected_commands = {
            "DL:01,C1,00,18,0A,FF,FF,00,00": "DL:P"
        }
        self.machine.coils["c_allow_enable"].enable()
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
