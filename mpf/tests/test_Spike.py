import time

from mpf.platforms.spike.spike import SpikePlatform

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSerial


class MockSpikeSocket(MockSerial):

    def read(self, length):
        del length
        if not self.queue:
            raise AssertionError("Read when no data is available!")
        msg = self.queue.pop()

        # currently needed for the bridge
        encoded_msg = "".join("%02x " % b for b in msg).encode()

        return encoded_msg

    def read_ready(self):
        return bool(self.queue)

    def write_ready(self):
        return True

    def write(self, encoded_msg):
        # currently needed for the bridge
        if encoded_msg == '\n\r'.encode():
            return len(encoded_msg)
        msg = bytearray()
        for i in range(int(len(encoded_msg) / 3)):
            msg.append(int(encoded_msg[i * 3:(i * 3) + 2], 16))

        msg = bytes(msg)

        if msg in self.permanent_commands:
            self.queue.append(self.permanent_commands[msg])
            return len(encoded_msg)

        # print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            self.crashed = True
            print("Unexpected command: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
            raise AssertionError("Unexpected command: " + "".join("\\x%02x" % b for b in msg) +
                                 " len: " + str(len(msg)))

        if len(self.expected_commands[msg]) != msg[-1]:
            print("Readback did not match")
            raise AssertionError("Readback did not match")

        if len(self.expected_commands[msg]) > 0:
            self.queue.append(self.expected_commands[msg])

        del self.expected_commands[msg]
        return len(encoded_msg)

    def __init__(self):
        super().__init__()
        self.name = "SerialMock"
        self.expected_commands = {}
        self.queue = []
        self.permanent_commands = {}
        self.crashed = False


class OPPCommon(MpfTestCase):

    def _checksummed_cmd(self, msg, read_back=0):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum])
        msg += bytes([read_back])
        return msg

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/spike/'

    def _mock_loop(self):
        self.clock.mock_serial("/dev/ttyUSB0", self.serialMock)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super().tearDown()

    def get_platform(self):
        return 'spike'

    def _wait_for_processing(self):
        start = time.time()
        while self.serialMock.expected_commands and not self.serialMock.crashed and time.time() < start + 10:
            self.advance_time_and_run(.01)

    def setUp(self):
        self.expected_duration = 1.5
        self.serialMock = MockSpikeSocket()

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x80\x02\xf1'): b'',
            self._checksummed_cmd(b'\x81\x03\xf0\x10'): b'',
            self._checksummed_cmd(b'\x81\x03\xf0\x20'): b'',
            self._checksummed_cmd(b'\x88\x03\xf0\x10'): b'',
            self._checksummed_cmd(b'\x88\x03\xf0\x20'): b'',
            self._checksummed_cmd(b'\x89\x03\xf0\x10'): b'',
            self._checksummed_cmd(b'\x89\x03\xf0\x20'): b'',
            self._checksummed_cmd(b'\x8a\x03\xf0\x10'): b'',
            self._checksummed_cmd(b'\x8a\x03\xf0\x20'): b'',
            self._checksummed_cmd(b'\x8b\x03\xf0\x10'): b'',
            self._checksummed_cmd(b'\x8b\x03\xf0\x20'): b'',
            self._checksummed_cmd(b'\x81\x02\xfe', 12): b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',    # TODO: fix response
            self._checksummed_cmd(b'\x81\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x88\x02\xfe', 12): b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',    # TODO: fix response
            self._checksummed_cmd(b'\x88\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x89\x02\xfe', 12): b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',    # TODO: fix response
            self._checksummed_cmd(b'\x89\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x8a\x02\xfe', 12): b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',    # TODO: fix response
            self._checksummed_cmd(b'\x8a\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x8b\x02\xfe', 12): b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',    # TODO: fix response
            self._checksummed_cmd(b'\x8b\x02\xf5', 4): b'\x00\x00\x00\x00',
        }
        self.serialMock.permanent_commands = {
            self._checksummed_cmd(b'\x80\x03\xf0\x22'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x03\xf0\x11'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x02\x11', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',    # read inputs
            self._checksummed_cmd(b'\x81\x02\x11', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',  # read inputs
            self._checksummed_cmd(b'\x88\x02\x11', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',  # read inputs
            self._checksummed_cmd(b'\x89\x02\x11', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',  # read inputs
            self._checksummed_cmd(b'\x8a\x02\x11', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',  # read inputs
            self._checksummed_cmd(b'\x8b\x02\x11', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',  # read inputs
            self._checksummed_cmd(b'\x81\x02\xff', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x81\x03\xfa\x00', 12): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x88\x02\xff', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x88\x03\xfa\x00', 12): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x89\x02\xff', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x89\x03\xfa\x00', 12): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x8a\x02\xff', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x8a\x03\xfa\x00', 12): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x8b\x02\xff', 10): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            self._checksummed_cmd(b'\x8b\x03\xfa\x00', 12): b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            b'\x00': b'\00',

        }
        super().setUp()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x22')]
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x11')]

    def testSetup(self):
        pass