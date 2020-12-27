import time
from unittest.mock import patch, MagicMock, call
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSerial


class SmartMatrixSerial(MockSerial):

    def __init__(self):
        super().__init__()
        self.type = None
        self.receive_data = b''

    def write_ready(self):
        return True

    def write(self, msg):
        self.receive_data += msg
        return len(msg)

    def stop(self):
        pass


class TestSmartMatrix(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/smart_matrix/'

    def get_platform(self):
        return False

    def serial_connect(self, port, baud):
        return self.serial_mocks[port]

    def setUp(self):
        self.serial_mocks = {"com4": MagicMock(), "com5": MagicMock()}

        with patch('mpf.platforms.smartmatrix.serial.Serial', self.serial_connect, create=True):
            super().setUp()

    def test_smart_matrix(self):
        # test new cookie
        self.serial_mocks["com4"].write = MagicMock()
        self.serial_mocks["com5"].write = MagicMock()
        self.machine.rgb_dmds["smartmatrix_1"].update(bytes([0x00, 0x01, 0x02, 0x03]))
        self.advance_time_and_run(.1)
        start = time.time()
        while self.serial_mocks["com4"].write.call_count < 2 and time.time() < start + 10:
            time.sleep(.001)
        self.serial_mocks["com4"].write.assert_has_calls([
            call(b'\xba\x11\x00\x03\x14\x7f\x00\x00'),                  # brightness
            call(b'\xba\x11\x00\x03\x04\x00\x00\x00\x00\x01\x02\x03')   # frame
            ])

        #test old cookie
        self.machine.rgb_dmds["smartmatrix_2"].update(bytes([0x00, 0x01, 0x02, 0x03]))
        self.advance_time_and_run(.1)
        start = time.time()
        while self.serial_mocks["com5"].write.call_count < 1 and time.time() < start + 10:
            time.sleep(.001)
        self.serial_mocks["com5"].write.assert_has_calls([
            call(b'\x01\x00\x01\x02\x03')                               # frame
            ])

