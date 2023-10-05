# mpf.tests.test_Fast

from mpf.tests.test_Fast import TestFastBase


class TestFastRetro(TestFastBase):
    """Tests the FAST Retro platform"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net_retro']

    def get_config_file(self):
        return 'retro.yaml'

    def create_expected_commands(self):
        # All of the device lookups will be tested via the initial config commands that are sent
        # Everything else is covered in the Neuron tests

        self.serial_connections['net_retro'].expected_commands = {

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
            "DL:0D,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:0E,81,00,10,0A,FF,00,FF,00": "DL:P",
            "DL:0F,81,00,10,0E,FF,00,01,00": "DL:P",
            "DL:10,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:11,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:20,81,00,10,0F,FF,00,00,00": "DL:P",
            "DL:21,81,00,10,0A,FF,00,FF,00": "DL:P",
            }

        # self.serial_connections['net_retro'].expected_commands['SL:L'] = (
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
            self.assertEqual(1, len(self.machine.default_platform.io_boards))
            self.assertEqual(96, self.machine.default_platform.io_boards[0].switch_count)
            self.assertEqual(48, self.machine.default_platform.io_boards[0].driver_count)

            for conn in self.serial_connections.values():
                self.assertFalse(conn.expected_commands)

        # If a test is testing a bad config file and causes a startup exception,
        # the machine will shut down. Safety check before we add futures to the loop.
        if not self.machine.is_shutting_down:
            self.advance_time_and_run(1)

    def test_matrix_lights(self):
        # test enable of matrix light
        self.serial_connections['net_retro'].expected_commands = {"L1:23,FF": "L1:P",}
        self.machine.lights["test_pdb_light"].on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        # test enable of matrix light with brightness
        self.serial_connections['net_retro'].expected_commands = {"L1:23,80": "L1:P",}
        self.machine.lights["test_pdb_light"].on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        # test disable of matrix light
        self.serial_connections['net_retro'].expected_commands = {"L1:23,00": "L1:P",}
        self.machine.lights["test_pdb_light"].off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        # test disable of matrix light with brightness
        self.serial_connections['net_retro'].expected_commands = {"L1:23,00": "L1:P",
                                                                  "L1:23,54": "L1:P",
                                                                  "L1:23,A8": "L1:P",
                                                                  "L1:23,FC": "L1:P",
                                                                  "L1:23,FF": "L1:P",}
        self.machine.lights["test_pdb_light"].on(brightness=255, fade_ms=100)
        self.advance_time_and_run(1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

    def test_gi_lights(self):
        # test gi on
        test_gi = self.machine.lights["test_gi"]
        self.serial_connections['net_retro'].expected_commands = {
            "GI:00,FF": "GI:P",
        }
        test_gi.on()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        self.serial_connections['net_retro'].expected_commands = {
            "GI:00,80": "GI:P",
        }
        test_gi.on(brightness=128)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        self.serial_connections['net_retro'].expected_commands = {
            "GI:00,F5": "GI:P",
        }
        test_gi.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        # test gi off
        self.serial_connections['net_retro'].expected_commands = {
            "GI:00,00": "GI:P",
        }
        test_gi.off()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        self.serial_connections['net_retro'].expected_commands = {
            "GI:00,F5": "GI:P",
        }
        test_gi.on(brightness=245)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)

        self.serial_connections['net_retro'].expected_commands = {
            "GI:00,00": "GI:P",
        }
        test_gi.on(brightness=0)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serial_connections['net_retro'].expected_commands)
