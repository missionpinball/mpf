"""Test Stern Spike Platform."""
import time

from mpf.platforms.spike.spike import SpikePlatform

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSerial


class MockSpikeSocket(MockSerial):

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

    def write(self, encoded_msg):
        """Write message."""
        # currently needed for the bridge
        if encoded_msg == '\n\r'.encode() or encoded_msg == b'\x03reset\n':
            return len(encoded_msg)

        if encoded_msg == "/bin/bridge 921600\r\n".encode():
            self.queue.append(b'MPF Spike Bridge!\r\n')
            return len(encoded_msg)

        msg = encoded_msg

        msg = bytes(msg)

        if msg in self.permanent_commands and msg not in self.expected_commands:
            self.queue.append("".join("%02x " % b for b in self.permanent_commands[msg]).encode())
            return len(encoded_msg)

        # ignore SendKey
        if len(msg) == 21 and msg[1] == 18 and msg[2] == 0xF3:
            return len(encoded_msg)

        # ignore wait
        if len(msg) == 2 and msg[0] == 1:
            return len(encoded_msg)

        # print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            self.crashed = True
            print("Unexpected command: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
            raise AssertionError("Unexpected command: " + "".join("\\x%02x" % b for b in msg) +
                                 " len: " + str(len(msg)))

        if len(msg) > 1 and len(self.expected_commands[msg]) != msg[-1]:
            print("Readback did not match")
            raise AssertionError("Readback did not match for msg {} and resp: {} {}".format(
                "".join("\\x%02x" % b for b in msg),
                len(self.expected_commands[msg]), self.expected_commands[msg]
            ))

        if len(self.expected_commands[msg]) > 0:
            self.queue.append("".join("%02x " % b for b in self.expected_commands[msg]).encode())

        del self.expected_commands[msg]
        return len(encoded_msg)

    def __init__(self):
        super().__init__()
        self.name = "SerialMock"
        self.expected_commands = {}
        self.queue = []
        self.permanent_commands = {}
        self.crashed = False


class SpikePlatformTest(MpfTestCase):

    def _checksummed_cmd(self, msg, read_back=0):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum])
        msg += bytes([read_back])
        return msg

    def _checksummed_response(self, msg):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum])
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
            self._checksummed_cmd(b'\x81\x02\xfe', 12):
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x81\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x88\x02\xfe', 12):
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x88\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x89\x02\xfe', 12):
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x89\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x8a\x02\xfe', 12):
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x8a\x02\xf5', 4): b'\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x8b\x02\xfe', 12):
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            self._checksummed_cmd(b'\x8b\x02\xf5', 4): b'\x00\x00\x00\x00',
        }
        self.serialMock.permanent_commands = {
            self._checksummed_cmd(b'\x80\x03\xf0\x22'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x03\xf0\x11'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
            self._checksummed_cmd(b'\x81\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
            self._checksummed_cmd(b'\x88\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
            self._checksummed_cmd(b'\x89\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
            self._checksummed_cmd(b'\x8a\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
            self._checksummed_cmd(b'\x8b\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
            self._checksummed_cmd(b'\x81\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x81\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x88\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x88\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x89\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x89\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8a\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8a\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8b\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8b\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            b'\x00': b'\00',

        }
        super().setUp()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x22')]
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x11')]

    def testPlatform(self):
        self._testCoils()
        self._testCoilRules()
        self._testLeds()
        self._testSwitches()
        self._testDmd()

    def _testCoils(self):
        # test board string
        self.assertEqual("Spike Node 1", self.machine.coils.c_test.hw_driver.get_board_name())

        # test pulse
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\xff\x80\x00\xff\x00\x00\x00\x00'): b''
        }
        self.machine.coils.c_test.pulse()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # test enable
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\xff\x80\x00\x9f\xff\x01\x00\x00'): b''
        }
        self.machine.coils.c_test.enable()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # second enable should do nothing
        self.machine.coils.c_test.enable()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # should repeat command after 250ms
        self.advance_time_and_run(.240)
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\x9f\xff\x01\x9f\xff\x01\x00\x00'): b''
        }
        self.advance_time_and_run(.020)
        self.assertFalse(self.serialMock.expected_commands)

        # disable coil
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.coils.c_test.disable()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # no more enables
        self.advance_time_and_run(.250)

    def _testCoilRules(self):
        # pop bumbers
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x7f\x0c\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x44\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofires.ac_pops.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofires.ac_pops.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # pop bumbers with inverted switch
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x7f\x0c\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofires.ac_pops2.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofires.ac_pops2.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # single-wound flippers
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\xff\x0c\x00\x9f\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x00\x00\x00\x06\x05'): b''
        }
        self.machine.flippers.f_test_single.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers.f_test_single.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # dual-wound flippers without EOS
        self.serialMock.expected_commands = {
            # main should be pulsed only
            self._checksummed_cmd(b'\x88\x19\x41\x01\xff\x0c\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x00\x00\x00\x01\x00'): b'',

            # hold should be pulsed and then pwmed (100% here)
            self._checksummed_cmd(b'\x88\x19\x41\x03\xff\x0c\x00\xff\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x00\x00\x00\x06\x05'): b''
        }
        self.machine.flippers.f_test_hold.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x19\x41\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers.f_test_hold.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # dual-wound flippers with eos
        self.serialMock.expected_commands = {
            # main should be pulsed and disabled when eos is hit (or timed). retriggers when eos is released.
            self._checksummed_cmd(b'\x88\x19\x41\x01\xff\x0c\x00\x9f\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x4f\x00\x02\x06\x00'): b'',

            # hold should be pulsed and then pwmed (100% here)
            self._checksummed_cmd(b'\x88\x19\x41\x03\xff\x0c\x00\xff\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x00\x00\x00\x06\x05'): b''
        }
        self.machine.flippers.f_test_hold_eos.enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # this is send twice due to MPF internals. will fix in the future
        self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')] = b''

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x19\x41\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers.f_test_hold_eos.disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        del self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')]

    def _testSwitches(self):
        self.assertSwitchState("s_start", False)
        # board 1 has a change
        self.serialMock.expected_commands = {
            b'\x00': b'\x01',
            self._checksummed_cmd(b'\x81\x02\x11', 10):
                self._checksummed_response(b'\xff\xf7\xff\xff\xff\xff\xff\xff\x00'),    # read inputs
        }

        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)

        self.assertSwitchState("s_start", True)

    def _testLeds(self):
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x80\x04\x80\x00\xff'): b''
        }
        self.machine.lights.backlight.color([255, 255, 255])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x80\x04\x80\x00\x64'): b''
        }
        self.machine.lights.backlight.color([100, 100, 100])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x04\x8a\x00\xaa'): b'',
            self._checksummed_cmd(b'\x81\x04\x8b\x00\xbb'): b'',
            self._checksummed_cmd(b'\x81\x04\x8c\x00\xcc'): b'',
        }
        self.machine.lights.l_rgb_insert.color([0xaa, 0xbb, 0xcc])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

    def _testDmd(self):
        self.serialMock.permanent_commands = {
            b'\x80\x00\x90\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55': b'',
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55': b'',
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33': b'',
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f': b'',
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00': b'',
            b'\x00\xf0\x00': b'',
            b'\x00': b'\x00',
        }

        frame = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 128, 128, 128, 128, 0, 0, 0, 0] * 128
        self.machine.dmds.spike_dmd.update(frame)
        self.advance_time_and_run()
