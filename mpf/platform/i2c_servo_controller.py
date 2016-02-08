""" I2C servo controller platform
"""

import logging
from mpf.core.platform import Platform
import time


class HardwarePlatform(Platform):
    """Supports the PCA9685/PCA9635 chip via I2C"""

    def __init__(self, machine):
        super().__init__(machine)
        self.log = logging.getLogger("I2C Servo Controller Platform")
        self.log.debug("Configuring template hardware interface.")
        self.config = self.machine.config['servo_controller']
        self.platform = None

    def __repr__(self):
        """String name you'd like to show up in logs and stuff when a
        reference to this platform is printed."""
        return '<Platform.I2C_Servo_Controller_Platform>'

    def initialize(self):
        """
        Method is called after all hardware platforms where instantiated
        """
        super().initialize()

        # validate our config (has to be in intialize since config_processor its not read in __init__)
        self.machine.config_validator.process_config2("servo_controllers", self.config)

        # load i2c platform
        self.platform = self.machine.get_platform_sections("i2c", self.config['platform'])

        # initialise PCA9685/PCA9635
        self.platform.i2c_write8(self.config['address'], 0x00,
                                 0x11)  # set sleep
        self.platform.i2c_write8(self.config['address'], 0x01,
                                 0x04)  # configure output
        self.platform.i2c_write8(self.config['address'], 0xFE,
                                 130)  # set approx 50Hz
        time.sleep(.01) # needed according to datasheet to sync PLL
        self.platform.i2c_write8(self.config['address'], 0x00,
                                 0x01)  # no more sleep
        time.sleep(.01) # needed to end sleep according to datasheet

    def servo_go_to_position(self, number, position):
        """
        Args:
            number: Number of servo 0 to 15
            position: Position to set the servo. 0 to 1

        """

        # check bounds
        if number < 0 or number > 15:
            raise AssertionError("invalid number")

        # check bounds
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # actual values depend on the controller. usually 150 to 600. interpolate
        servo_min = self.config['servo_min']
        servo_max = self.config['servo_max']
        value = int(servo_min + position * (servo_max - servo_min))

        # set servo via i2c
        self.platform.i2c_write8(self.config['address'], 0x06 + number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x07 + number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x08 + number * 4,
                                 value & 0xFF)
        self.platform.i2c_write8(self.config['address'], 0x09 + number * 4,
                                 value >> 8)
