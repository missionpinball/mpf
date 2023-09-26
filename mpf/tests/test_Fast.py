# mpf.tests.test_Fast

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.platforms.fast import (MockFastDmd, MockFastExp,
                                      MockFastNetNano, MockFastNetNeuron,
                                      MockFastRgb, MockFastSeg, MockFastNetRetro)


class TestFastBase(MpfTestCase):
    """Tests FAST Neuron hardware."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = []
        self.serial_connections = dict()

    def get_config_file(self):
        raise NotImplementedError

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
                self.net_cpu = self.serial_connections['net2']
            elif conn == 'exp':
                self.serial_connections['exp'] = MockFastExp(self)  # default com4
                self.exp_cpu = self.serial_connections['exp']
            elif conn == 'rgb':
                self.serial_connections['rgb'] = MockFastRgb(self)  # default com5
                self.rgb_cpu = self.serial_connections['rgb']
            elif conn == 'net1':
                self.serial_connections['net1'] = MockFastNetNano(self)  # default com6
                self.net_cpu = self.serial_connections['net1']
            elif conn == 'net_retro':
                self.serial_connections['net_retro'] = MockFastNetRetro(self)  # default com6
                self.net_cpu = self.serial_connections['net_retro']
            elif conn == 'seg':
                self.serial_connections['seg'] = MockFastSeg(self)  # default com7
                self.seg_cpu = self.serial_connections['seg']
            elif conn == 'dmd':
                self.serial_connections['dmd'] = MockFastDmd(self)  # default com8
                self.dmd_cpu = self.serial_connections['dmd']

    def confirm_commands(self):
        self.advance_time_and_run(.1)
        for conn in self.serial_connections.values():
            self.assertFalse(conn.expected_commands)

    def create_expected_commands(self):
        # These is everything that happens based on this config file before the
        # code in the test starts. (These commands also do lots of tests themselves.),
        # including initial switch and driver states.

        # TODO move these since they're Neuron specific
        self.serial_connections['net2'].expected_commands = {
            # Initial switch responses before they're configured which apply to all tests:
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
            }

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
            for conn in self.serial_connections.values():
                self.assertFalse(conn.expected_commands)

        # If a test is testing a bad config file and causes a startup exception,
        # the machine will shut down. Safety check before we add futures to the loop.
        if not self.machine.is_shutting_down:
            self.advance_time_and_run(1)
