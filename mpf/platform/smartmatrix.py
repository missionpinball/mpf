"""Contains code for an SmatrMatrix Shield connected to a Teensy"""
# smartmatrix.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import serial
import sys
import threading
import traceback
from mpf.system.platform import Platform


class HardwarePlatform(Platform):

    def __init__(self, machine):

        super(HardwarePlatform, self).__init__(machine)

        self.log = logging.getLogger("SmartMatrix")
        self.log.debug("Configuring SmartMatrix hardware interface.")

        self.dmd_frame = bytearray()

    def __repr__(self):
        return '<Platform.SmartMatrix>'

    def configure_dmd(self):

        self.log.debug("configuring smart matrix dmd")

        self.machine.events.add_handler('timer_tick', self.tick)

        self.serial_port = serial.Serial(port='com12', baudrate=2500000)

        return self

    def update(self, data):
        try:
            self.dmd_frame = bytearray(data)
        except TypeError:
            pass

    def tick(self):
        pass
        # send the dmd data

        self.serial_port.write(bytearray([0x01]))
        self.serial_port.write(self.dmd_frame)




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
