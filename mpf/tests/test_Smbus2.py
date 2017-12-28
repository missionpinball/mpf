from mpf.tests.MpfTestCase import MpfTestCase, patch, MagicMock


class TestSmbus2(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/smbus2/'

    def get_platform(self):
        # no force platform. we are testing smbus2
        return False

    def setUp(self):
        self.smbus = MagicMock()
        with patch("smbus2.SMBus") as SMBus:
            SMBus.return_value = self.smbus
            super().setUp()
            SMBus.assert_called_once_with(1)

    def test_i2c(self):
        self.machine.default_platform.i2c_write8(17, 23, 1337)
        self.smbus.write_byte_data.assert_called_once_with(17, 23, 1337)

        self.smbus.read_byte_data = MagicMock(return_value=1337)
        self.assertEqual(1337, self.machine.default_platform.i2c_read8(17, 23))
        self.smbus.read_byte_data.assert_called_once_with(17, 23)