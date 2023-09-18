"""I2C servo controller platform."""
import asyncio
import logging

from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.core.platform import ServoPlatform


class I2CServoControllerHardwarePlatform(ServoPlatform):

    """Supports the PCA9685/PCA9635 chip via I2C."""

    def __init__(self, machine):
        """initialize I2C servo platform."""
        super().__init__(machine)
        self.config = self.machine.config_validator.validate_config("servo_controllers",
                                                                    self.machine.config.get('servo_controllers', {}))
        self.platform = None
        self.i2c_devices = {}
        self.features['tickless'] = True
        self._configure_device_logging_and_debug("I2C Servo Controller", self.config)

    def __repr__(self):
        """Return string representation."""
        return '<Platform.I2C_Servo_Controller_Platform>'

    async def initialize(self):
        """initialize platform."""
        await super().initialize()
        # load i2c platform
        self.platform = self.machine.get_platform_sections(
            "i2c", self.config['platform'])
        self.platform.assert_has_feature("i2c")

    async def _initialize_controller(self, address):
        # check if controller is already initialized
        if address in self.i2c_devices:
            return self.i2c_devices[address]

        i2c_device = await self.platform.configure_i2c(address)
        self.i2c_devices[address] = i2c_device

        # initialize PCA9685/PCA9635
        i2c_device.i2c_write8(0x00, 0x11)  # set sleep
        i2c_device.i2c_write8(0x01, 0x04)  # configure output
        i2c_device.i2c_write8(0xFE, 130)   # set approx 50Hz
        await asyncio.sleep(.01)     # needed according to datasheet to sync PLL
        i2c_device.i2c_write8(0x00, 0x01)  # no more sleep
        await asyncio.sleep(.01)     # needed to end sleep according to datasheet
        return i2c_device

    async def configure_servo(self, number: str, config: dict):
        """Configure servo."""
        del config
        try:
            i2c_address, servo_number = number.rsplit("-", 1)
        except ValueError:
            servo_number = number
            i2c_address = str(0x40)
        try:
            number_int = int(servo_number)
        except ValueError:
            raise ConfigFileError("Invalid servo number {} in {}.".format(servo_number, number),
                                  2, self.log.name if self.log else "")

        i2c_device = await self._initialize_controller(i2c_address)

        # check bounds
        if number_int < 0 or number_int > 15:
            raise ConfigFileError("Invalid number {} in {}. The controller only supports servos 0 to 15.".format(
                number_int, number), 1, self.log.name if self.log else "")

        return I2cServo(number_int, self.config, i2c_device)

    def stop(self):
        """Stop platform."""


class I2cServo(ServoPlatformInterface):

    """A servo hw device."""

    def __init__(self, number, config, i2c_device):
        """initialize I2C hw servo."""
        self.log = logging.getLogger('I2cServo')
        self.number = number
        self.config = config
        self.i2c_device = i2c_device

    def go_to_position(self, position):
        """Move servo to position.

        Args:
        ----
            position: Position to set the servo. 0 to 1

        """
        # check bounds
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # actual values depend on the controller. usually 150 to 600.
        # interpolate
        servo_min = self.config['servo_min']
        servo_max = self.config['servo_max']
        value = int(servo_min + position * (servo_max - servo_min))

        # set servo via i2c
        self.i2c_device.i2c_write8(0x06 + self.number * 4, 0)
        self.i2c_device.i2c_write8(0x07 + self.number * 4, 0)
        self.i2c_device.i2c_write8(0x08 + self.number * 4, value & 0xFF)
        self.i2c_device.i2c_write8(0x09 + self.number * 4, value >> 8)

    def stop(self):
        """Disable servo."""
        self.i2c_device.i2c_write8(0x06 + self.number * 4, 0)
        self.i2c_device.i2c_write8(0x07 + self.number * 4, 0)
        self.i2c_device.i2c_write8(0x08 + self.number * 4, 0)
        self.i2c_device.i2c_write8(0x09 + self.number * 4, 0)

    def set_speed_limit(self, speed_limit):
        """Not implemented."""

    def set_acceleration_limit(self, acceleration_limit):
        """Not implemented."""
