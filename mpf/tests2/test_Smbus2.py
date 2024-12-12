import asyncio

from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch


class TestSmbus2(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/smbus2/'

    def get_platform(self):
        # no force platform. we are testing smbus2
        return False

    def setUp(self):
        smbus = patch('mpf.platforms.smbus2.SMBus2Asyncio')
        self.smbus = smbus.start()
        self.smbus_instance = MagicMock()
        self.smbus.return_value = self.smbus_instance
        self.addCleanup(self.smbus.stop)
        super().setUp()

    def test_i2c(self):
        result = asyncio.Future()
        result.set_result(True)
        self.smbus_instance.write_byte_data = MagicMock(return_value=result)

        device = self.loop.run_until_complete(self.machine.default_platform.configure_i2c("1-17"))

        device.i2c_write8(23, 1337)
        self.machine_run()
        self.smbus_instance.write_byte_data.assert_called_once_with(17, 23, 1337)
        self.smbus.assert_called_once_with('1')

        result = asyncio.Future()
        result.set_result(1337)
        self.smbus_instance.read_byte_data = MagicMock(return_value=result)
        self.assertEqual(1337, self.loop.run_until_complete(device.i2c_read8(23)))
        self.smbus_instance.read_byte_data.assert_called_once_with(17, 23)
