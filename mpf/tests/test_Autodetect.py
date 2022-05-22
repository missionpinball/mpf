from collections import namedtuple
from serial.tools import list_ports
from unittest.mock import MagicMock

from mpf.exceptions.runtime_error import MpfRuntimeError
from mpf.platforms import autodetect
from mpf.tests.MpfTestCase import MpfTestCase

WINDOWS_PORTS = ['TEST', 'FOO', 'COM0', 'COM1', 'COM2', 'COM3', 'tty']
MAC_PORTS = ['/dev/tty', '/dev/cu.usb', '/dev/tty.usbmodem0', '/dev/tty.usbmodem1', '/dev/tty.usbmodem2', '/dev/tty.usbmodem3']
LINUX_PORTS = ['/dev/Bluetooth', '/dev/foo', '/dev/cu.ACM0', '/dev/cu.ACM1', '/dev/cu.ACM2', '/dev/cu.ACM3']
NO_PORTS = ['/dev/tty', 'COMX', '/dev/tty.usbmodem', 'foo']


class TestAutoDetect(MpfTestCase):

    def mock_ports(self, ports):
        mock = []
        MockPort = namedtuple('MockPort', ['device'])
        for port in ports:
            mock_port = MockPort(port)
            mock.append(mock_port)
        return mock

    def test_smartmatrix(self):
        autodetect._find_fast_quad = MagicMock(return_value=["/a", "/b", "/c"])
        result = autodetect.autodetect_smartmatrix_dmd_port()
        self.assertEqual(result, "/a")

    def test_retro(self):
        for ports in (WINDOWS_PORTS, MAC_PORTS, LINUX_PORTS):
            list_ports.comports = MagicMock(return_value=self.mock_ports(ports))
            result = autodetect.autodetect_fast_ports(is_retro=True)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0], ports[2])

        list_ports.comports = MagicMock(return_value=self.mock_ports(NO_PORTS))
        with self.assertRaises(MpfRuntimeError):
            autodetect.autodetect_fast_ports(is_retro=True)

    def test_quad(self):
        for ports in (WINDOWS_PORTS, MAC_PORTS, LINUX_PORTS):
            list_ports.comports = MagicMock(return_value=self.mock_ports(ports))
            result = autodetect.autodetect_fast_ports()
            self.assertEqual(len(result), 4)
            self.assertEqual(result, ports[2:6])

        list_ports.comports = MagicMock(return_value=self.mock_ports(NO_PORTS))
        with self.assertRaises(MpfRuntimeError):
            autodetect.autodetect_fast_ports(is_retro=True)
