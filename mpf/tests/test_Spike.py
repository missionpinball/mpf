"""Test Stern Spike Platform."""
import time
import serial_asyncio

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
        total_msg_len = len(encoded_msg)
        while encoded_msg:
            if encoded_msg == '\n\r'.encode() or encoded_msg == b'\x03reset\n' or encoded_msg[0] == 0xf5:
                return len(encoded_msg)
            if encoded_msg == "/bin/bridge 921600 SPIKE1 2>/dev/null\r\n".encode():
                self.queue.append(b'MPF Spike Bridge!\r\n')
                return len(encoded_msg)
            if encoded_msg[0] == 0x00:
                self._handle_msg(encoded_msg[0:1])
                encoded_msg = encoded_msg[1:]
            elif encoded_msg[0] == 0x01:
                self._handle_msg(encoded_msg[0:2])
                encoded_msg = encoded_msg[2:]
            elif encoded_msg[0] == 0x80 and encoded_msg[2] == 0x90:
                self._handle_msg(encoded_msg[0:2051])
                encoded_msg = encoded_msg[2051:]
            else:
                msg_len = encoded_msg[1] + 3
                self._handle_msg(encoded_msg[0:msg_len])
                encoded_msg = encoded_msg[msg_len:]

        return total_msg_len

    def _handle_msg(self, encoded_msg):
        if bytearray(encoded_msg) == bytearray(b'\x00'):
            # special case for poll
            if self.dirty_nodes:
                if self.dirty_nodes[0] == 0:
                    self.queue.append(bytes(bytearray([0xf0])))
                else:
                    self.queue.append(bytes(bytearray([self.dirty_nodes[0]])))
            else:
                # everything clean
                self.queue.append(b'\x00')
            return len(encoded_msg)

        msg = encoded_msg

        msg = bytes(msg)

        if msg and msg[0] & 0x80 and (msg[2] == 0x11 or (msg[2] == 0xf0 and msg[3] == 0x10)):

            try:
                self.dirty_nodes.remove(msg[0] & 0x0f)
            except:
                pass

        if msg in self.permanent_commands and msg not in self.expected_commands:
            if msg[0] & 0x80 > 0 and len(self.permanent_commands[msg]) != msg[-1] and len(msg) < 255:
                print("Readback did not match")
                raise AssertionError("Readback did not match for msg {} and resp: {} {}".format(
                    "".join("\\x%02x" % b for b in msg),
                    len(self.permanent_commands[msg]), self.permanent_commands[msg]
                ))
            self.queue.append(self.permanent_commands[msg])
            return len(encoded_msg)

        # ignore SendKey
        if len(msg) == 21 and msg[1] == 18 and msg[2] == 0xF3:
            return len(encoded_msg)

        # ignore wait
        if len(msg) == 2 and msg[0] == 1:
            return len(encoded_msg)

        # print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            print(self.permanent_commands)
            self.crashed = True
            print("Unexpected command: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
            raise AssertionError("Unexpected command: " + "".join("\\x%02x" % b for b in msg) +
                                 " len: " + str(len(msg)))

        if msg[0] & 0x80 > 0 and len(self.expected_commands[msg]) != msg[-1]:
            print("Readback did not match")
            raise AssertionError("Readback did not match for msg {} and resp: {} {}".format(
                "".join("\\x%02x" % b for b in msg),
                len(self.expected_commands[msg]), self.expected_commands[msg]
            ))

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
        self.dirty_nodes = []


class SpikePlatformTest(MpfTestCase):

    @staticmethod
    def _checksummed_cmd(msg, read_back=0):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum])
        msg += bytes([read_back])
        return msg

    @staticmethod
    def _checksummed_response(msg):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum, 0])
        return msg

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
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

        self.serialMock.dirty_nodes = [0, 1, 8, 9, 10, 11]

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x80\x02\xf1'): b'',
            b'\x03\x00\x03': b'\x01\x00\x03',   # GetBridgeVersion
            b'\x05\x00\x01': b'\x18',           # GetBridgeState
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
                self._checksummed_response(b'\x01\x00\x12\x04\x2b\xd0\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x88\x02\xfe', 12):
                self._checksummed_response(b'\x08\x00\x12\x04\x2b\x90\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x89\x02\xfe', 12):
                self._checksummed_response(b'\x09\x00\x12\x04\x2b\xd0\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x8a\x02\xfe', 12):
                self._checksummed_response(b'\x0a\x00\x12\x04\x2b\xd0\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x8b\x02\xfe', 12):
                self._checksummed_response(b'\x0b\x00\x12\x04\x2b\xd0\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x81\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x81\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x41\x7c\x33\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x81\x03\xf9\x01', 18):
                self._checksummed_response(b'\x70\xfe\xd5\x55\x70\xfe\xd5\x55\x64\x00\x65\x00\x7a\x06\x00\x00'),
            self._checksummed_cmd(b'\x88\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x88\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x88\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x88\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x89\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x89\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x89\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x89\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x8a\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8a\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8a\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x8a\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x8b\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8b\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x8b\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x8b\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x8a\x08\x32\x00\xc8\x00\x00\x4a\xff'): b'',        # Configure stepper
            self._checksummed_cmd(b'\x8a\x06\x31\x00\xc8\x00\x0a'): b'',                # Stepper Move
        }
        self.serialMock.permanent_commands = {
            self._checksummed_cmd(b'\x80\x03\xf0\x22'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x03\xf0\x11'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x81\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x88\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x89\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x8a\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x8b\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x81\x02\xff', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x81\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x88\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x89\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x8a\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x8b\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            b'\x06\x02\x45\x03\x00': b'',  # SetResponseTime

        }
        super().setUp()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.dirty_nodes)
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x22')]
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x11')]

        # this seems to happen in real spike
        self.serialMock.dirty_nodes = [0, 1, 8, 9, 10, 11]
        self.advance_time_and_run()

    def testPlatform(self):
        self._testCoils()
        self._testCoilRules()
        self._testLeds()
        self._testSwitches()
        self._testDmd()
        self._testStepper()

    def _testCoils(self):
        # test board string
        self.assertEqual("Spike Node 1", self.machine.coils["c_test"].hw_driver.get_board_name())

        # test pulse
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\xff\x80\x00\xff\x00\x00\x00\x00'): b''
        }
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # test enable
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\xff\x80\x00\x9f\xff\x01\x00\x00'): b''
        }
        self.machine.coils["c_test"].enable()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # second enable should do nothing
        self.machine.coils["c_test"].enable()
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
        self.machine.coils["c_test"].disable()
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
        self.machine.autofire_coils["ac_pops"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofire_coils["ac_pops"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # pop bumbers with inverted switch
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x7f\x0c\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofire_coils["ac_pops2"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofire_coils["ac_pops2"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # single-wound flippers
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\xff\x0c\x00\x9f\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x00\x00\x00\x06\x05'): b''
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers["f_test_single"].disable()
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
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x19\x41\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # dual-wound flippers with eos
        self.serialMock.expected_commands = {
            # main should be pulsed and disabled when eos is hit (or timed). retriggers when eos is released.
            self._checksummed_cmd(b'\x88\x19\x41\x01\xff\x0c\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x4f\x00\x02\x06\x00'): b'',

            # hold should be pulsed and then pwmed (100% here)
            self._checksummed_cmd(b'\x88\x19\x41\x03\xff\x0c\x00\xff\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x4d\x00\x00\x00\x06\x05'): b''
        }
        self.machine.flippers["f_test_hold_eos"].enable()
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
        self.machine.flippers["f_test_hold_eos"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        del self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x19\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')]

    def _testSwitches(self):
        self.assertSwitchState("s_start", False)
        # board 1 has a change
        self.serialMock.dirty_nodes = [1]
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x02\x11', 10):
                self._checksummed_response(b'\xff\xf7\xff\xff\xff\xff\xff\xff'),    # read inputs
        }

        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.dirty_nodes)

        self.assertSwitchState("s_start", True)

    def _testLeds(self):
        self.serialMock.expected_commands = {
            b'\x09\x02\xff\xff\x00': b''
        }
        self.machine.lights["backlight"].color([255, 255, 255])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x09\x02\x64\x64\x00': b''
        }
        self.machine.lights["backlight"].color([100, 100, 100])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # batched light updates
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\x00\xaa\xbb\xcc'): b'',
        }
        self.machine.lights["l_rgb_insert"].color([0xaa, 0xbb, 0xcc])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # batched light updates with common fade
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\x80\x00\x00\x00'): b'',
        }
        self.machine.lights["l_rgb_insert"].color([0x00, 0x00, 0x00], fade_ms=100)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # batched light updates with multiple fades
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\xfd\x55\x5d\x66'): b'',
            self._checksummed_cmd(b'\x81\x06\x8a\xfd\x54\x5d\x65'): b'',
        }
        self.machine.lights["l_rgb_insert"].color([0xaa, 0xbb, 0xcc], fade_ms=198 * 2)
        self.advance_time_and_run(.1)
        self.assertEqual(1, len(self.serialMock.expected_commands))     # first fade
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\xfd\xaa\xbb\xcc'): b'',
        }
        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)

    def _testDmd(self):
        if serial_asyncio.__version__ == '0.4':
            return

        self.serialMock.permanent_commands = {
            b'\x80\x00\x90\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00': b'',
            b'\x00': b'\x00',
        }

        frame = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 128, 128, 128, 128, 0, 0, 0, 0] * 128
        self.machine.dmds["spike_dmd"].update(frame)
        self.advance_time_and_run()

    def _testStepper(self):
        self.mock_event("stepper_stepper1_ready")
        # trigger home switch
        self.assertSwitchState("s_stepper_home", False)
        # board 10 has a change
        self.serialMock.dirty_nodes = [10]
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x8a\x02\x11', 10):
                self._checksummed_response(b'\xf0\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x8a\x08\x32\x00\xc8\x00\x00\x4a\xff'): b'',    # stop stepper
            self._checksummed_cmd(b'\x8a\x03\x34\x00'): b''                         # stepper set home
        }

        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.dirty_nodes)

        self.assertSwitchState("s_stepper_home", True)

        self.serialMock.permanent_commands[self._checksummed_cmd(b'\x8a\x02\x38', 7)] = self._checksummed_response(
            b'\x00\x00\x00\x00\x00')

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x8a\x06\x31\x00\xc8\x00\x14'): b''
        }
        self.assertEventCalled("stepper_stepper1_ready")
        self.mock_event("stepper_stepper1_ready")

        self.post_event("test_01")
        self.advance_time_and_run(.05)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertEventNotCalled("stepper_stepper1_ready")

        self.serialMock.permanent_commands[self._checksummed_cmd(b'\x8a\x02\x38', 7)] = self._checksummed_response(
            b'\xc8\x00\x00\x00\x00')
        self.advance_time_and_run(.05)
        self.assertEventCalledWith("stepper_stepper1_ready", position=200)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x8a\x06\x31\x00\xf4\x01\x14'): b''
        }
        self.assertEventCalled("stepper_stepper1_ready")
        self.mock_event("stepper_stepper1_ready")

        self.post_event("test_10")
        self.advance_time_and_run(.05)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertEventNotCalled("stepper_stepper1_ready")

        self.serialMock.permanent_commands[self._checksummed_cmd(b'\x8a\x02\x38', 7)] = self._checksummed_response(
            b'\xf4\x01\x00\x00\x00')
        self.advance_time_and_run(.05)
        self.assertEventCalledWith("stepper_stepper1_ready", position=500)


class SpikePlatformFirmware0_49Test(MpfTestCase):

    @staticmethod
    def _checksummed_cmd(msg, read_back=0):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum])
        msg += bytes([read_back])
        return msg

    @staticmethod
    def _checksummed_response(msg):
        checksum = SpikePlatform._checksum(msg)
        msg += bytes([checksum, 0])
        return msg

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
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

        self.serialMock.dirty_nodes = [0, 1, 8, 9, 10, 11]

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x80\x02\xf1'): b'',
            b'\x03\x00\x03': b'\x01\x00\x03',   # GetBridgeVersion
            b'\x05\x00\x01': b'\x18',           # GetBridgeState
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
            self._checksummed_cmd(b'\x81\x02\xfe', 12):     # get version
                self._checksummed_response(b'\x01\x00\x31\x00\x2b\x90\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x88\x02\xfe', 12):
                self._checksummed_response(b'\x08\x00\x31\x00\x2b\x90\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x89\x02\xfe', 12):
                self._checksummed_response(b'\x09\x00\x31\x00\x2b\x90\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x8a\x02\xfe', 12):
                self._checksummed_response(b'\x0a\x00\x31\x00\x2b\x90\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x8b\x02\xfe', 12):
                self._checksummed_response(b'\x0b\x00\x31\x00\x2b\x90\x24\x25\x00\x05'),
            self._checksummed_cmd(b'\x81\x03\xfa\x00', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
            self._checksummed_cmd(b'\x81\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x41\x7c\x33\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x81\x03\xf9\x01', 18):
                self._checksummed_response(b'\x70\xfe\xd5\x55\x70\xfe\xd5\x55\x64\x00\x65\x00\x7a\x06\x00\x00'),
            self._checksummed_cmd(b'\x88\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x88\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x89\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x89\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x8a\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x8a\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x8b\x03\xf9\x00', 18):
                self._checksummed_response(b'\xff\xff\xff\xff\x01\x00\x02\x42\x06\x27\x09\x1f\x00\x08\x07\x00'),
            self._checksummed_cmd(b'\x8b\x03\xf9\x01', 18):
                self._checksummed_response(b'\x8a\x5c\x5f\x56\x8a\x5c\x5f\x56\x64\x00\x65\x00\x0a\x34\x00\x00'),
            self._checksummed_cmd(b'\x8a\x08\x32\x00\xc8\x00\x00\x4a\xff'): b'',        # Configure stepper
            self._checksummed_cmd(b'\x8a\x06\x31\x00\xc8\x00\x0a'): b'',                # Stepper Move
            self._checksummed_cmd(b'\x81\x05\x70\x0b\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x88\x05\x70\x03\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x88\x05\x70\x04\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x88\x05\x70\x05\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x88\x05\x70\x0d\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x88\x05\x70\x0f\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x8a\x05\x70\x01\x05\x05'): b'',  # set debounce
            self._checksummed_cmd(b'\x88\x0c\x43\x08\x00\x05\x06\x07\x01\x04\x03\x02\x08', 3):
                self._checksummed_response(b'\x00'),  # set coil priorities
            self._checksummed_cmd(b'\x8b\x0c\x43\x08\x00\x01\x03\x05\x06\x07\x02\x04\x08', 3):
                self._checksummed_response(b'\x00'),  # set coil priorities
            self._checksummed_cmd(b'\x81\x06\x14\x10\x00\x16\x00'): b'',                # SetNumLEDsInputs,
            self._checksummed_cmd(b'\x88\x06\x14\x38\x00\x10\x00'): b'',                # SetNumLEDsInputs,
        }
        for node in [b'\x81', b'\x88', b'\x89', b'\x8a', b'\x8b']:
            additional_commands = {
                self._checksummed_cmd(node + b'\x06\x14\x60\x00\x40\x00'): b'',                # SetNumLEDsInputs,
                self._checksummed_cmd(node + b'\x04\x46\xff\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0e\x72\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'): b'',
                self._checksummed_cmd(node + b'\x04\x48\x06\x00'): b'',                        # SetOCTime
                self._checksummed_cmd(node + b'\x04\x46\xfe\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x00\xff\x01\x00\x00\x00\x00\x00\x00'): b'',    # pulse
                self._checksummed_cmd(node + b'\x04\x46\xfd\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x01\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\xfb\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x02\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\xf7\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x03\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\xef\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x04\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\xdf\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x05\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\xbf\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x06\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\x7f\x01'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0b\x40\x07\xff\x01\x00\x00\x00\x00\x00\x00'): b'',  # pulse
                self._checksummed_cmd(node + b'\x04\x46\x00\x00'): b'',                        # CoilSetMask
                self._checksummed_cmd(node + b'\x0e\x72\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
                self._checksummed_cmd(node + b'\x04\x48\x80\x00'): b'',                        # SetOCTime
                self._checksummed_cmd(node + b'\x03\x44\x01'): b'',                            # SetOCTime
            }
            self.serialMock.expected_commands.update(additional_commands)

        self.serialMock.permanent_commands = {
            self._checksummed_cmd(b'\x80\x03\xf0\x22'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x03\xf0\x11'): b'',    # send twice during init
            self._checksummed_cmd(b'\x80\x02\x11', 10):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff'),    # read inputs
            self._checksummed_cmd(b'\x81\x02\x11', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x0b\x00'),    # read inputs
            self._checksummed_cmd(b'\x88\x02\x11', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x0b\x00'),    # read inputs
            self._checksummed_cmd(b'\x89\x02\x11', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x0b\x00'),    # read inputs
            self._checksummed_cmd(b'\x8a\x02\x11', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x0b\x00'),    # read inputs
            self._checksummed_cmd(b'\x8b\x02\x11', 12):
                self._checksummed_response(b'\xff\xff\xff\xff\xff\xff\xff\xff\x0b\x00'),    # read inputs
            self._checksummed_cmd(b'\x81\x02\xff', 10):
                self._checksummed_response(b'\xf4\x02\x00\x00\x00\x00\x00\x00'),
            self._checksummed_cmd(b'\x81\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x88\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x89\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x8a\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            self._checksummed_cmd(b'\x8b\x04\xf5\xff\x00', 4):
                self._checksummed_response(b'\x00\x00'),
            b'\x06\x02\x45\x03\x00': b'',  # SetResponseTime
            self._checksummed_cmd(b'\x81\x02\xff', 10):
                self._checksummed_response(b'\x3a\x01\x00\x00\x00\x00\x00\x00'),
            self._checksummed_cmd(b'\x81\x03\xfa\x00', 12):
                self._checksummed_response(b'\xf0\x03\x00\x00\x91\xea\x05\x00\x82\x01'),
            self._checksummed_cmd(b'\x88\x02\xff', 10):
                self._checksummed_response(b'\x32\x00\x00\x00\x00\x00\x00\x00'),
            self._checksummed_cmd(b'\x88\x03\xfa\x00', 12):
                self._checksummed_response(b'\x0a\x24\x00\x00\xb9\x03\x36\x00\x81\x01'),
            self._checksummed_cmd(b'\x89\x02\xff', 10):
                self._checksummed_response(b'\x4b\x00\x00\x00\x00\x00\x00\x00'),
            self._checksummed_cmd(b'\x89\x03\xfa\x00', 12):
                self._checksummed_response(b'\x27\x2e\x00\x00\xcf\xae\x44\x00\x7e\x01'),
            self._checksummed_cmd(b'\x8a\x02\xff', 10):
                self._checksummed_response(b'\x4b\x00\x00\x00\x00\x00\x00\x00'),
            self._checksummed_cmd(b'\x8a\x03\xfa\x00', 12):
                self._checksummed_response(b'\x82\x38\x00\x00\x3f\xe2\x53\x00\x7d\x01'),
            self._checksummed_cmd(b'\x8b\x02\xff', 10):
                self._checksummed_response(b'\x4b\x00\x00\x00\x00\x00\x00\x00'),
            self._checksummed_cmd(b'\x8b\x03\xfa\x00', 12):
                self._checksummed_response(b'\xec\x03\x00\x00\x34\xd5\x05\x00\x7e\x01'),

        }
        super().setUp()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.dirty_nodes)
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x22')]
        del self.serialMock.permanent_commands[self._checksummed_cmd(b'\x80\x03\xf0\x11')]

        # this seems to happen in real spike
        self.serialMock.dirty_nodes = [0, 1, 8, 9, 10, 11]
        self.advance_time_and_run()

    def testPlatform(self):
        self._testCoils()
        self._testCoilRules()
        self._testLeds()
        self._testSwitches()
        self._testDmd()
        self._testStepper()

    def _testCoils(self):
        # test board string
        self.assertEqual("Spike Node 1", self.machine.coils["c_test"].hw_driver.get_board_name())

        # test pulse
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\xff\x80\x00\xff\x00\x00\x00\x00'): b''
        }
        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # test enable
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x0b\x40\x00\xff\x80\x00\x9f\xff\x01\x00\x00'): b''
        }
        self.machine.coils["c_test"].enable()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # second enable should do nothing
        self.machine.coils["c_test"].enable()
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
        self.machine.coils["c_test"].disable()
        self.advance_time_and_run(.001)
        self.assertFalse(self.serialMock.expected_commands)

        # no more enables
        self.advance_time_and_run(.250)

    def _testCoilRules(self):
        # pop bumbers
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x0a\x7f\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x05\x70\x04\x02\x02'): b'',  # set debounce
        }
        self.machine.autofire_coils["ac_pops"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.autofire_coils["ac_pops"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # pop bumbers with inverted switch
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x0a\x7f\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x05\x70\x05\x02\x02'): b'',  # set debounce
        }
        self.machine.autofire_coils["ac_pops2"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
        }
        self.machine.autofire_coils["ac_pops2"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # single-wound flippers without EOS
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x01\xff\x0c\x00\x9f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x4d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x05'): b'',
            self._checksummed_cmd(b'\x88\x05\x70\x0d\x02\x02'): b'',  # set debounce
        }
        self.machine.flippers["f_test_single"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers["f_test_single"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # dual-wound flippers without EOS
        self.serialMock.expected_commands = {
            # main should be pulsed only
            self._checksummed_cmd(b'\x88\x24\x41\x01\xff\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x4d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00'): b'',

            # hold should be pulsed and then pwmed (100% here)
            self._checksummed_cmd(b'\x88\x24\x41\x03\xff\x0c\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x4d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x05'): b''
        }
        self.machine.flippers["f_test_hold"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x24\x41\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers["f_test_hold"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # single-wound with EOS
        self.serialMock.expected_commands = {
            # main should be pulsed and disabled when eos is hit (or timed). retriggers when eos is released.
            self._checksummed_cmd(b'\x88\x24\x41\x01\xff\x0c\x00\x9f\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x4d\x00\x00\x4f\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x00'): b'',
            self._checksummed_cmd(b'\x88\x05\x70\x0f\x02\x02'): b'',  # set debounce
        }
        self.machine.flippers["f_test_single_eos"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # this is send twice due to MPF internals. will fix in the future
        self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')] = b''

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers["f_test_single_eos"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        del self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')]

        # dual-wound flippers with eos
        self.serialMock.expected_commands = {
            # main should be pulsed and disabled when eos is hit (or timed). retriggers when eos is released.
            self._checksummed_cmd(b'\x88\x24\x41\x01\xff\x0c\x00\x00\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x4d\x00\x00\x4f\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x00'): b'',
            # hold should be pulsed and then pwmed (100% here)
            self._checksummed_cmd(b'\x88\x24\x41\x03\xff\x0c\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x4d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x05'): b'',
            # debouce is already set because of the previous flipper rule
            #self._checksummed_cmd(b'\x88\x05\x70\x0f\x02\x02'): b'',  # set debounce
        }
        self.machine.flippers["f_test_hold_eos"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # this is send twice due to MPF internals. will fix in the future
        self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')] = b''

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x88\x24\x41\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b'',
            self._checksummed_cmd(b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): b''
        }
        self.machine.flippers["f_test_hold_eos"].disable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        del self.serialMock.permanent_commands[self._checksummed_cmd(
            b'\x88\x24\x41\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')]

    def _testSwitches(self):
        self.assertSwitchState("s_start", False)
        # board 1 has a change
        self.serialMock.dirty_nodes = [1]
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x02\x11', 12):
                self._checksummed_response(b'\xff\xf7\xff\xff\xff\xff\xff\xff\x00\x00'),    # read inputs
        }

        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.dirty_nodes)

        self.assertSwitchState("s_start", True)

    def _testLeds(self):
        self.serialMock.expected_commands = {
            b'\x09\x02\xff\xff\x00': b''
        }
        self.machine.lights["backlight"].color([255, 255, 255])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x09\x02\x64\x64\x00': b''
        }
        self.machine.lights["backlight"].color([100, 100, 100])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # batched light updates
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\x00\xaa\xbb\xcc'): b'',
        }
        self.machine.lights["l_rgb_insert"].color([0xaa, 0xbb, 0xcc])
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # batched light updates with common fade
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\x80\x00\x00\x00'): b'',
        }
        self.machine.lights["l_rgb_insert"].color([0x00, 0x00, 0x00], fade_ms=100)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)

        # batched light updates with multiple fades
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\xfd\x55\x5d\x66'): b'',
        }
        self.machine.lights["l_rgb_insert"].color([0xaa, 0xbb, 0xcc], fade_ms=198 * 2)
        self.advance_time_and_run(.1)
        self.assertFalse(self.serialMock.expected_commands)     # first fade
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x81\x06\x8a\xfd\xaa\xbb\xcc'): b'',
        }
        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)

    def _testDmd(self):
        if serial_asyncio.__version__ == '0.4':
            return

        self.serialMock.permanent_commands = {
            b'\x80\x00\x90\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55'
            b'\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0'
            b'\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x55\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33'
            b'\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0'
            b'\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x33\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f'
            b'\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0\x00\x0f\x00\xf0'
            b'\x00\x0f\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0'
            b'\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00'
            b'\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00\x00\x00\xf0\x00': b'',
            b'\x00': b'\x00',
        }

        frame = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 0, 0, 0, 128, 128, 128, 128, 0, 0, 0, 0] * 128
        self.machine.dmds["spike_dmd"].update(frame)
        self.advance_time_and_run()

    def _testStepper(self):
        self.mock_event("stepper_stepper1_ready")
        # trigger home switch
        self.assertSwitchState("s_stepper_home", False)
        # board 10 has a change
        self.serialMock.dirty_nodes = [10]
        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x8a\x02\x11', 12):
                self._checksummed_response(b'\xf0\xff\xff\xff\xff\xff\xff\xff\x00\x00'),    # read inputs
            self._checksummed_cmd(b'\x8a\x08\x32\x00\xc8\x00\x00\x4a\xff'): b'',    # stop stepper
            self._checksummed_cmd(b'\x8a\x03\x34\x00'): b''                         # stepper set home
        }

        self.advance_time_and_run(.2)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.dirty_nodes)

        self.assertSwitchState("s_stepper_home", True)

        self.serialMock.permanent_commands[self._checksummed_cmd(b'\x8a\x02\x38', 7)] = self._checksummed_response(
            b'\x00\x00\x00\x00\x00')

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x8a\x06\x31\x00\xc8\x00\x14'): b''
        }
        self.assertEventCalled("stepper_stepper1_ready")
        self.mock_event("stepper_stepper1_ready")

        self.post_event("test_01")
        self.advance_time_and_run(.05)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertEventNotCalled("stepper_stepper1_ready")

        self.serialMock.permanent_commands[self._checksummed_cmd(b'\x8a\x02\x38', 7)] = self._checksummed_response(
            b'\xc8\x00\x00\x00\x00')
        self.advance_time_and_run(.05)
        self.assertEventCalledWith("stepper_stepper1_ready", position=200)

        self.serialMock.expected_commands = {
            self._checksummed_cmd(b'\x8a\x06\x31\x00\xf4\x01\x14'): b''
        }
        self.assertEventCalled("stepper_stepper1_ready")
        self.mock_event("stepper_stepper1_ready")

        self.post_event("test_10")
        self.advance_time_and_run(.05)
        self.assertFalse(self.serialMock.expected_commands)
        self.assertEventNotCalled("stepper_stepper1_ready")

        self.serialMock.permanent_commands[self._checksummed_cmd(b'\x8a\x02\x38', 7)] = self._checksummed_response(
            b'\xf4\x01\x00\x00\x00')
        self.advance_time_and_run(.05)
        self.assertEventCalledWith("stepper_stepper1_ready", position=500)
