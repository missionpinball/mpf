"""Test MyPinballs Platform."""
import time

from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSerial


class MockMypinballsSocket(MockSerial):

    """Serial mock."""

    def read(self, length):
        """Read from serial."""
        del length
        if not self.queue:
            return b''
        msg = self.queue.pop()

        return msg

    def read_ready(self):
        """True if ready to read."""
        return bool(self.queue)

    def write_ready(self):
        """True if ready to write."""
        return True

    def write(self, msg):
        """Write message."""
        parts = msg.split(b'\n')

        # remove last newline
        assert parts.pop() == b''

        for part in parts:
            self._handle_msg(part)

        return len(msg)

    def _handle_msg(self, msg):
        if msg in self.permanent_commands and msg not in self.expected_commands:
            self.queue.append(self.permanent_commands[msg])
            return len(msg)

        # print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            self.crashed = True
            raise AssertionError("Unexpected command: " + msg.decode() + "(" + "".join("\\x%02x" % b for b in msg) +
                                 ") len: " + str(len(msg)))

        if self.expected_commands[msg] is not False:
            self.queue.append(self.expected_commands[msg])

        del self.expected_commands[msg]

        return len(msg)

    def __init__(self):
        super().__init__()
        self.name = "SerialMock"
        self.expected_commands = {}
        self.queue = []
        self.permanent_commands = {}
        self.crashed = False


class MyPinballsPlatformTest(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/mypinballs/'

    def _mock_loop(self):
        self.clock.mock_serial("/dev/ttyUSB0", self.serialMock)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super().tearDown()

    def get_platform(self):
        return False

    def _wait_for_processing(self):
        start = time.time()
        while self.serialMock.expected_commands and not self.serialMock.crashed and time.time() < start + 10:
            self.advance_time_and_run(.01)

    def setUp(self):
        self.serialMock = MockMypinballsSocket()

        # all display are reset at startup
        self.serialMock.expected_commands = {
            b'3:1': False,
            b'3:2': False,
            b'3:6': False,
        }
        self.serialMock.permanent_commands = {}
        super().setUp()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)

    def testPlatform(self):
        self.serialMock.expected_commands = {
            b'1:1:???1234': False,
        }
        self.machine.segment_displays["display1"].add_text("1234", key="score")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # change text (with same key)
        self.serialMock.expected_commands = {
            b'1:1:???1337': False,
        }
        self.machine.segment_displays["display1"].add_text("1337", key="score")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # change text (with same key)
        self.serialMock.expected_commands = {
            b'1:1:??42?23': False,
        }
        self.machine.segment_displays["display1"].add_text("42 23", key="score")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set to empty
        self.serialMock.expected_commands = {
            b'3:1': False,
        }
        self.machine.segment_displays["display1"].remove_text_by_key("score")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'1:2:?424242': False,
        }
        self.machine.segment_displays["display2"].add_text("424242")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'2:2:?424242': False,
        }
        self.machine.segment_displays["display2"].set_flashing(FlashingType.FLASH_ALL)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'1:2:?424242': False,
        }
        self.machine.segment_displays["display2"].set_flashing(FlashingType.NO_FLASH)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'4:2:?424242': False,
        }
        self.machine.segment_displays["display2"].set_flashing(FlashingType.FLASH_MATCH)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)
