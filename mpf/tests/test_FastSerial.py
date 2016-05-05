import unittest
from queue import Queue
from unittest.mock import MagicMock
from mpf.platforms import fast


class SerialMock:

    def read(self, length):
        del length
        if not self.send_buffer:
            msg = self.queue.get()
        else:
            msg = self.send_buffer.pop()
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
            self.send_buffer.append(self.permanent_commands[msg])
            return

        # print("Serial received: " + "".join("\\x%02x" % ord(b) for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            self.crashed = True
            raise AssertionError("Unexpected command: " + str(msg, 'UTF-8').rstrip() +
                                 " len: " + str(len(msg)))

        if self.expected_commands[msg] is not False:
            self.send_buffer.append(self.expected_commands[msg])

        del self.expected_commands[msg]

    def __init__(self):
        self.name = "SerialMock"
        self.send_buffer = []
        self.expected_commands = {}
        self.queue = Queue()
        self.permanent_commands = {}
        self.crashed = False
        self.read_buffer = b""


class TestFastSerial(unittest.TestCase):

    def test_SerialCommunicator_DMD(self):

        self.machine = MagicMock()
        self.platform = MagicMock()
        self.send_queue = Queue()
        self.receive_queue = Queue()

        self.serialMock = SerialMock()
        fast.serial.Serial = MagicMock(return_value=self.serialMock)

        self.serialMock.expected_commands = {
            'ID:\r'.encode(): 'ID:DMD FP-CPU-002-1 00.88\r\n'.encode()
        }

        self.communicator = fast.SerialCommunicator(
            machine=self.machine, platform=self.platform, port="port_name",
            baud=1234, send_queue=Queue(),
            receive_queue=self.receive_queue)

        self.platform.register_processor_connection.assert_called_with('DMD', self.communicator)

    def test_SerialCommunicator_RGB(self):
        self.machine = MagicMock()
        self.platform = MagicMock()
        self.send_queue = Queue()
        self.receive_queue = Queue()

        self.serialMock = SerialMock()
        fast.serial.Serial = MagicMock(return_value=self.serialMock)

        self.serialMock.expected_commands = {
            'ID:\r'.encode(): 'ID:RGB FP-CPU-002-1 00.88\r\n'.encode()
        }

        self.communicator = fast.SerialCommunicator(
            machine=self.machine, platform=self.platform, port="port_name",
            baud=1234, send_queue=Queue(),
            receive_queue=self.receive_queue)

        self.platform.register_processor_connection.assert_called_with('RGB', self.communicator)

    def test_SerialCommunicator_NET(self):
        self.machine = MagicMock()
        self.platform = MagicMock()
        self.platform.machine_type = "fast"
        self.send_queue = Queue()
        self.receive_queue = Queue()

        self.serialMock = SerialMock()
        fast.serial.Serial = MagicMock(return_value=self.serialMock)

        self.serialMock.expected_commands = {
            'ID:\r'.encode(): 'ID:NET FP-CPU-002-1 00.88\r'.encode(),
            'NN:0\r'.encode(): 'NN:0,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:1\r'.encode(): 'NN:1,asd,0.87,8,10,,,,,,\r\r'.encode(),
            'NN:2\r'.encode(): 'NN:2,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:3\r'.encode(): 'NN:3,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:4\r'.encode(): 'NN:4,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:5\r'.encode(): 'NN:5,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:6\r'.encode(): 'NN:6,asd,0.87,8,10,,,,,,\r'.encode(),
            'NN:7\r'.encode(): 'NN:7,asd,0.87,8,10,,,,,,\r'.encode(),
        }

        self.communicator = fast.SerialCommunicator(
            machine=self.machine, platform=self.platform, port="port_name",
            baud=1234, send_queue=Queue(),
            receive_queue=self.receive_queue)

        self.platform.register_processor_connection.assert_called_with('NET', self.communicator)
