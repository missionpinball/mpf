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

    def getConfigFile(self):
        if self._testMethodName == "test_smart_matrix_old_cookie":
            return 'old_cookie.yaml'
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/smart_matrix/'

    def get_platform(self):
        return 'smartmatrix'

    def setUp(self):
        self.serial = SmartMatrixSerial()
        super().setUp()

    def _mock_loop(self):
        self.clock.mock_serial("com4", self.serial)

    def test_smart_matrix(self):
        self.machine.default_platform.update([0x00, 0x01, 0x02, 0x03])
        self.advance_time_and_run()
        self.assertEqual(b'\xba\x11\x00\x03\x04\x00\x00\x00\x00\x01\x02\x03', self.serial.receive_data)

    def test_smart_matrix_old_cookie(self):
        self.machine.default_platform.update([0x00, 0x01, 0x02, 0x03])
        self.advance_time_and_run()
        self.assertEqual(b'\x01\x00\x01\x02\x03', self.serial.receive_data)
