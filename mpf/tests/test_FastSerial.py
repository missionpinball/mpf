import unittest
from queue import Queue
from unittest.mock import MagicMock, call

import time

from mpf.platforms.fast import fast


class SerialMock:

    def read(self, length):
        del length
        msg = self.queue.get()
        return msg

    def __getattr__(self, item):
        pass

    def tell(self):
        return True

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return False

    def close(self):
        return True

    def flush(self):
        return True

    def readline(self):
        return self.read(100)

    def readinto(self, buffer):
        length = len(buffer)
        if len(self.read_buffer) < length:
            self.read_buffer += self.read(length)
        buffer[:length] = self.read_buffer[:length]
        self.read_buffer = self.read_buffer[length:]
        return length

    def write(self, msg):
        if msg in self.permanent_commands:
            self.queue.put(self.permanent_commands[msg])
            return

        # print("Serial received: " + "".join("\\x%02x" % ord(b) for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            self.crashed = True
            raise AssertionError("Unexpected command: " + str(msg, 'UTF-8').rstrip() +
                                 " len: " + str(len(msg)))

        if self.expected_commands[msg] is not False:
            self.queue.put(self.expected_commands[msg])

        del self.expected_commands[msg]

    def __init__(self):
        self.name = "SerialMock"
        self.expected_commands = {}
        self.queue = Queue()
        self.permanent_commands = {}
        self.crashed = False
        self.read_buffer = b""


class TestFastSerial(unittest.TestCase):

    def setUp(self):
        self.machine = MagicMock()
        self.platform = MagicMock()
        self.platform.config['debug'] = True
        self.platform.machine_type = "fast"
        self.send_queue = Queue()
        self.receive_queue = Queue()

        self.serialMock = SerialMock()
        fast.serial.Serial = MagicMock(return_value=self.serialMock)

    def test_SerialCommunicator_DMD(self):
        self.serialMock.expected_commands = {
            'ID:\r'.encode(): 'ID:DMD FP-CPU-002-1 00.88\r'.encode(),
            ((' ' * 256) + '\r').encode(): False
        }

        self.communicator = fast.SerialCommunicator(
            machine=self.machine, platform=self.platform, port="port_name",
            baud=1234, send_queue=Queue(),
            receive_queue=self.receive_queue)

        self.platform.register_processor_connection.assert_called_with('DMD', self.communicator)
        self.assertFalse(self.serialMock.expected_commands)

        self.communicator.send("test".encode())
        self.serialMock.expected_commands = {
            'BM:test'.encode(): False
        }
        time.sleep(.001)
        for dummy_i in range(10):
            if not self.serialMock.expected_commands:
                break
            time.sleep(.1)

        self.assertFalse(self.serialMock.expected_commands)

    def test_SerialCommunicator_RGB(self):
        self.serialMock.expected_commands = {
            'ID:\r'.encode(): 'ID:RGB FP-CPU-002-1 00.88\r'.encode(),
            ((' ' * 256) + '\r').encode(): False
        }

        self.communicator = fast.SerialCommunicator(
            machine=self.machine, platform=self.platform, port="port_name",
            baud=1234, send_queue=Queue(),
            receive_queue=self.receive_queue)

        self.platform.register_processor_connection.assert_called_with('RGB', self.communicator)
        self.assertFalse(self.serialMock.expected_commands)

    def test_SerialCommunicator_NET(self):
        self.serialMock.expected_commands = {
            'ID:\r'.encode(): 'ID:NET FP-CPU-002-1 00.88\r'.encode(),
            'NN:0\r'.encode(): 'NN:0,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:1\r'.encode(): 'NN:1,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:2\r'.encode(): 'NN:2,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:3\r'.encode(): 'NN:3,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:4\r'.encode(): 'NN:4,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:5\r'.encode(): 'NN:5,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:6\r'.encode(): 'NN:6,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:7\r'.encode(): 'NN:7,asd,0.87,8,10,,,,,,\r'.encode(),
            ((' ' * 256) + '\r').encode(): False,
        }

        self.communicator = fast.SerialCommunicator(
            machine=self.machine, platform=self.platform, port="port_name",
            baud=1234, send_queue=Queue(),
            receive_queue=self.receive_queue)

        self.assertFalse(self.serialMock.expected_commands)

        self.platform.register_processor_connection.assert_called_with('NET', self.communicator)
        self.platform.log.info.assert_has_calls([
            call('Connecting to %s at %sbps', 'port_name', 1234),
        ])

        self.platform.log.debug.assert_has_calls([
            call('Querying FAST IO boards...'),
            call('Fast IO Board 0: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 1: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 2: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 3: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 4: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 5: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 6: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8'),
            call('Fast IO Board 7: Model: asd, Firmware: 0.87, Switches: 16, Drivers: 8')
        ])

        self.communicator.send("SA:")
        self.serialMock.expected_commands = {
            "SA:\r".encode(): "SA:1,00,8,00000000\r".encode()
        }
        time.sleep(.001)
        for dummy_i in range(10):
            if not self.serialMock.expected_commands and not self.communicator.receive_queue.empty():
                break
            time.sleep(.1)

        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.communicator.receive_queue.empty())
        self.assertEqual("SA:1,00,8,00000000", self.communicator.receive_queue.get())
