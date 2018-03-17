"""I2C servo controller platform."""
import asyncio
import logging
import time

from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.core.platform import ServoPlatform


class I2CServoControllerHardwarePlatform(ServoPlatform):

    """Supports the PCA9685/PCA9635 chip via I2C."""

    def __init__(self, machine):
        """Initialise I2C servo platform."""
        super().__init__(machine)
        self.log = logging.getLogger("I2C Servo Controller Platform")
        self.log.debug("Configuring template hardware interface.")
        self.config = self.machine.config['servo_controllers']
        self.platform = None
        self.features['tickless'] = True

    def __repr__(self):
        """Return string representation."""
        return '<Platform.I2C_Servo_Controller_Platform>'

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        yield from super().initialize()

        # validate our config (has to be in intialize since config_processor
        # is not read in __init__)
        self.machine.config_validator.validate_config("servo_controllers",
                                                      self.config)

        # load i2c platform
        self.platform = self.machine.get_platform_sections(
            "i2c", self.config['platform'])

        # initialise PCA9685/PCA9635
        self.platform.i2c_write8(self.config['address'], 0x00,
                                 0x11)  # set sleep
        self.platform.i2c_write8(self.config['address'], 0x01,
                                 0x04)  # configure output
        self.platform.i2c_write8(self.config['address'], 0xFE,
                                 130)  # set approx 50Hz
        yield from asyncio.sleep(.01, loop=self.machine.clock.loop)     # needed according to datasheet to sync PLL
        self.platform.i2c_write8(self.config['address'], 0x00,
                                 0x01)  # no more sleep
        yield from asyncio.sleep(.01, loop=self.machine.clock.loop)     # needed to end sleep according to datasheet

    def configure_servo(self, number: str):
        """Configure servo."""
        number_int = int(number)

        # check bounds
        if number_int < 0 or number_int > 15:
            raise AssertionError("invalid number")

        return I2cServo(number_int, self.config, self.platform)

    def stop(self):
        """Stop platform."""
        pass


class I2cServo(ServoPlatformInterface):

    """A servo hw device."""

    def __init__(self, number, config, platform):
        """Initialise I2C hw servo."""
        self.log = logging.getLogger('I2cServo')
        self.number = number
        self.config = config
        self.platform = platform

    def go_to_position(self, position):
        """Move servo to position.

        Args:
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
        self.platform.i2c_write8(self.config['address'], 0x06 + self.number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x07 + self.number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x08 + self.number * 4,
                                 value & 0xFF)
        self.platform.i2c_write8(self.config['address'], 0x09 + self.number * 4,
                                 value >> 8)

    @classmethod
    def set_speed_limit(cls, speed_limit):
        """Todo emulate speed parameter."""
        pass

    @classmethod
    def set_acceleration_limit(cls, acceleration_limit):
        """Todo emulate acceleration parameter."""
        pass
