""" Contains the ServoController """
# Written by Jan Kantert
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

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
        super(ServoController, self).__init__(machine, name, config, collection,
                                     platform_section='servo_controllers',
                                     validate=validate)

        # currently only implemented for PCA9685/PCA9635
        self.platform.i2c_write8(self.config['address'], 0x00, 0x11) # set sleep
        self.platform.i2c_write8(self.config['address'], 0x01, 0x04) # configure output
        self.platform.i2c_write8(self.config['address'], 0xFE, 130) # set approx 50Hz
        time.sleep(.01)
        self.platform.i2c_write8(self.config['address'], 0x00, 0x01) # no more sleep
        time.sleep(.01)

    def go_to_position(self, number, position):
        if number < 0 or number > 7:
            raise AssertionError("invalid number")

        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        servo_min = self.config['servo_min']
        servo_max = self.config['servo_max']
        value = int(servo_min + position * (servo_max - servo_min))

        self.platform.i2c_write8(self.config['address'], 0x06 + number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x07 + number * 4, 0)
        self.platform.i2c_write8(self.config['address'], 0x08 + number * 4, value & 0xFF)
        self.platform.i2c_write8(self.config['address'], 0x09 + number * 4, value >> 8)


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
