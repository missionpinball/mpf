from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.platforms import openpixel
from mpf.tests.loop import MockSocket


class TestPlatform(MpfTestCase):

    def getConfigFile(self):
        return 'test_platform.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/platform/'

    def get_platform(self):
        return False

    def setUp(self):
        openpixel.OPCSerialSender = MagicMock()
        super().setUp()

    def _mock_loop(self):
        self._mock_socket = MockSocket()
        self.clock.mock_socket("localhost", 7890, self._mock_socket)

    def test_platform_from_device(self):
        # tests that a platform can be added by a device, even if it's not
        # specified in the hardware section

        self.assertEqual(self.machine.leds.led1.platform,
                         self.machine.hardware_platforms['smart_virtual'])

        self.assertEqual(self.machine.leds.led2.platform,
                         self.machine.hardware_platforms['fadecandy'])
