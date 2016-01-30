""" Contains the ServoController """

import time
import math
from mpf.system.device import Device


class ServoController(Device):
    """Implements a servo controller

    Args: Same as the Device parent class

    """

    config_section = 'servo_controllers'
    collection = 'servo_controllers'
    class_label = 'servo_controller'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super().__init__(machine, name, config, collection,
                         platform_section='servo_controllers',
                         validate=validate)

        # currently only implemented for PCA9685/PCA9635
        self.platform.i2c_write8(self.config['address'], 0x00,
                                 0x11)  # set sleep
        self.platform.i2c_write8(self.config['address'], 0x01,
                                 0x04)  # configure output
        self.platform.i2c_write8(self.config['address'], 0xFE,
                                 130)  # set approx 50Hz
        time.sleep(.01)
        self.platform.i2c_write8(self.config['address'], 0x00,
                                 0x01)  # no more sleep
        time.sleep(.01)

    def go_to_position(self, number, position):
        if number < 0 or number > 15:
            raise AssertionError("invalid number")

        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        servo_min = self.config['servo_min']
        servo_max = self.config['servo_max']
        value = int(servo_min + position * (servo_max - servo_min))

        self.platform.i2c_write8(self.config['address'], 0x06 + number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x07 + number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x08 + number * 4,
                                 value & 0xFF)
        self.platform.i2c_write8(self.config['address'], 0x09 + number * 4,
                                 value >> 8)
