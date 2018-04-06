import asyncio

from mpf.platforms import smbus2
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch


class TestSmbus2(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/smbus2/'

    def get_platform(self):
        # no force platform. we are testing smbus2
        return False

    def setUp(self):
        super().setUp()

    def test_i2c(self):
        with patch("mpf.platforms.smbus2.SMBus2Asyncio") as smbus:
            smbus_instance = MagicMock()
            smbus.return_value = smbus_instance
            result = asyncio.Future(loop=self.loop)
            result.set_result(True)
            smbus_instance.write_byte_data = MagicMock(return_value=result)

            self.machine.default_platform.i2c_write8("1-17", 23, 1337)
            self.machine_run()
            smbus_instance.write_byte_data.assert_called_once_with(17, 23, 1337)
            smbus.assert_called_once_with('1', loop=self.loop)

            result = asyncio.Future(loop=self.loop)
            result.set_result(1337)
            smbus_instance.read_byte_data = MagicMock(return_value=result)
            self.assertEqual(1337, self.loop.run_until_complete(self.machine.default_platform.i2c_read8("1-17", 23)))
            smbus_instance.read_byte_data.assert_called_once_with(17, 23)
