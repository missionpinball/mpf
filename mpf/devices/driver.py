""" Contains the Driver parent class. """
# driver.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time
from mpf.system.hardware import Device


class Driver(Device):
    """Generic class that holds driver objects.

    A 'driver' is any device controlled from a driver board which is typically
    the high-voltage stuff like coils and flashers.

    This class exposes the methods you can use on these driver types of
    devices. Each platform module (i.e. P-ROC, FAST, etc.) subclasses this
    class to actually communicate with the physitcal hardware and perform the
    actions.

    """

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Driver.' + name)
        super(Driver, self).__init__(machine, name, config, collection)

        # todo read these in and/or change to dict
        self.pulse_ms = 30
        self.pwm_on = 0
        self.pwm_off = 0


        self.time_last_changed = 0
        self.time_when_done = 0

        self.hw_driver = self.machine.platform.configure_driver(
            config)
        self.log.debug("Creating '%s' with config: %s", name, config)

        if 'pulse_ms' in config:
            self.pulse_ms = config['pulse_ms']
        if 'holdPatter' in config:
            self.pwm_on = int(config['holdPatter'].split('-')[0])
            self.pwm_off = int(config['holdPatter'].split('-')[1])

    def enable(self):
        # this is a temporary version of this method. The final version will
        # use a software-controlled hold for safety purposes like this:
        # get the secs per tick
        # set a pulse for 2.5x secs per tick
        # set a timer that runs each tick to re-up it
        self.log.debug("Enabling Driver: %s", self.name)
        self.time_when_done = -1
        self.time_last_changed = time.clock()
        self.hw_driver.enable()

    def disable(self):
        """ Disables this driver """
        self.log.debug("Disabling Driver: %s", self.name)
        self.time_last_changed = time.clock()
        self.hw_driver.enable()
        # todo also disable the timer which reenables this

    def pulse(self, milliseconds=None):
        """ Enables this driver.

        Parameters
        ----------

        milliseconds : int : optional
            The number of milliseconds the driver should be enabled for. If no
            value is provided, the driver will be enabled for the value
            specified in the config dictionary.

        """
        if milliseconds is None:
            milliseconds = self.pulse_ms
        elif milliseconds < 1:
            self.log.warning("Received command to pulse  Driver %s for %dms, "
                             "but ms is less than 1, so we're doing nothing.",
                             self.name, milliseconds)
            return
        # todo also disable the timer which reenables this
        self.log.debug("Pulsing Driver %s for %dms", self.name, milliseconds)
        self.hw_driver.pulse(int(milliseconds))
        self.time_last_changed = time.clock()
        self.time_when_done = self.time_last_changed + (milliseconds / 1000.0)

    def pwm(self, on_ms, _off_ms, orig_on_ms):
        pass  # todo
        self.time_last_changed = time.clock()
        self.time_when_done = -1
        # todo also disable the timer which reenables this

    def pulse_pwm(self):
        pass  # todo
        self.time_last_changed = time.clock()
        self.time_when_done = -1
        # todo also disable the timer which reenables this



# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
