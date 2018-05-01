import asyncio

from mpf.tests.MpfTestCase import MpfTestCase, patch


class TestMMA8451(MpfTestCase):

    def get_platform(self):
        return False

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mma8451/'

    @asyncio.coroutine
    def i2c_read8(self, register):
        return self.i2c_layout[register]

    @asyncio.coroutine
    def i2c_read_block(self, register, count):
        assert count == 6
        assert register == 0x01
        return self.read_value

    def i2c_write8(self, register, value):
        """Write to I2C."""
        key = (register, value)
        if key not in self.i2c_expect:
            raise AssertionError("Did not expect write to register {:02X} with value {:02X} ({})".
                                 format(register, value, key))
        del self.i2c_expect[key]

    def setUp(self):
        self.read_value = bytearray([0, 0, 0, 0, 0, 0])
        self.i2c_layout = {0x0D: 0x1A,      # ID of the device
                           0x2B: 00,        # reset success
                           }
        self.i2c_expect = {(0x2B, 0x40): True,  # reset
                           (0x2B, 0x02): True,  # resolution
                           (0x2D, 0x01): True,  # ready true
                           (0x2E, 0x01): True,  # ready true
                           (0x11, 0x40): True,  # orientation mode on
                           (0x2A, 0x2D): True,  # low noise and activate
                           }
        with patch("mpf.platforms.virtual.VirtualI2cDevice.i2c_read8", new=self.i2c_read8):
            with patch("mpf.platforms.virtual.VirtualI2cDevice.i2c_read_block", new=self.i2c_read_block):
                with patch("mpf.platforms.virtual.VirtualI2cDevice.i2c_write8", new=self.i2c_write8):
                    super().setUp()

        self.assertFalse(self.i2c_expect)

    def test_init_and_poll(self):
        with patch("mpf.platforms.virtual.VirtualI2cDevice.i2c_read8", new=self.i2c_read8):
            with patch("mpf.platforms.virtual.VirtualI2cDevice.i2c_read_block", new=self.i2c_read_block):
                with patch("mpf.platforms.virtual.VirtualI2cDevice.i2c_write8", new=self.i2c_write8):
                    self.assertEqual((0, 0, 0), self.machine.accelerometers.test_accelerometer.value)

                    self.read_value = bytearray([0, 0, 0, 0, 60, 10])
                    self.advance_time_and_run(.1)

                    self.assertEqual((0, 0, 9.199), self.machine.accelerometers.test_accelerometer.value)
