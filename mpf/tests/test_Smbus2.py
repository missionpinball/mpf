from mpf.platforms import smbus2
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock


class TestSmbus2(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/smbus2/'

    def get_platform(self):
        # no force platform. we are testing smbus2
        return False

    def setUp(self):
        smbus2.SMBus = MagicMock()
        self.smbus = MagicMock()
        smbus2.SMBus.return_value = self.smbus
        super().setUp()

    def test_i2c(self):
        self.machine.default_platform.i2c_write8("1-17", 23, 1337)
        self.smbus.write_byte_data.assert_called_once_with(17, 23, 1337)
        smbus2.SMBus.assert_called_once_with(1)

        self.smbus.read_byte_data = MagicMock(return_value=1337)
        self.assertEqual(1337, self.loop.run_until_complete(self.machine.default_platform.i2c_read8("1-17", 23)))
        self.smbus.read_byte_data.assert_called_once_with(17, 23)
