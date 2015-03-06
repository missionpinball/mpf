""" Contains the Driver parent class. """
# driver.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time
from mpf.system.devices import Device


class Driver(Device):
    """Generic class that holds driver objects.

    A 'driver' is any device controlled from a driver board which is typically
    the high-voltage stuff like coils and flashers.

    This class exposes the methods you should use on these driver types of
    devices. Each platform module (i.e. P-ROC, FAST, etc.) subclasses this
    class to actually communicate with the physical hardware and perform the
    actions.

    Args: Same as the Device parent class

    """

    config_section = 'Coils'
    collection = 'coils'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Driver.' + name)
        super(Driver, self).__init__(machine, name, config, collection)

        self.time_last_changed = 0
        self.time_when_done = 0

        # We save out number_str since the platform driver will convert the
        # number into a hardware number, but we need the original number for
        # some things later.
        self.config['number_str'] = str(config['number']).upper()

        self.hw_driver, self.number = self.machine.platform.configure_driver(
                                                                self.config)
        self.log.debug("Creating '%s' with config: %s", name, config)

        if 'pulse_ms' not in self.config:
            # If there's a holdPatter and no pulse_ms, we'll keep it at zero
            if 'holdPatter' in self.config:
                self.config['pulse_ms'] = 0
            # Otherwise we'll use the system default for pulse_ms
            else:
                self.config['pulse_ms'] = \
                    self.machine.config['MPF']['default_pulse_ms']

        if 'holdPatter' in self.config:
            self.config['pwm_on'] = int(config['holdPatter'].split('-')[0])
            self.config['pwm_off'] = int(config['holdPatter'].split('-')[1])
        else:
            self.config['pwm_on'] = 0
            self.config['pwm_off'] = 0

        if ('allow_enable' in self.config and
                str(self.config['allow_enable']).upper() == 'TRUE'):
            self.config['allow_enable'] = True
        else:
            self.config['allow_enable'] = False

    def enable(self):
        """Enables a driver by holding it 'on'.

        If this driver is configured with a holdPatter, then this method will use
        that holdPatter to pwm pulse the driver.

        If not, then this method will just enable the driver. As a safety
        precaution, if you want to enable() this driver without pwm, then you
        have to add the following option to this driver in your machine
        configuration files:

        allow_enable: True
        """
        if self.config['pwm_on'] and self.config['pwm_off']:
            self.pwm(self.config['pwm_on'], self.config['pwm_off'],
                     self.config['pulse_ms'])
        elif self.config['allow_enable']:
            self.hw_driver.enable()
        else:
            self.log.warning("Received a command to enable this coil without "
                             "pwm, but 'allow_enable' has not been set to True "
                             "in this coil's configuration.")

        self.time_when_done = -1
        self.time_last_changed = time.time()

    def disable(self):
        """ Disables this driver """
        self.log.debug("Disabling Driver: %s", self.name)
        self.time_last_changed = time.time()
        self.hw_driver.disable()
        # todo also disable the timer which reenables this

    def pulse(self, milliseconds=None, power=1.0):
        """ Pulses this driver.

        Args:
            milliseconds: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            power: A multiplier that will be applied to the default pulse time,
                typically a float between 0.0 and 1.0. (Note this is only used
                if milliseconds is not specified.)
        """
        if milliseconds is None:
            milliseconds = int(self.config['pulse_ms']) * power
        elif milliseconds < 1:
            self.log.warning("Received command to pulse  Driver %s for %dms, "
                             "but ms is less than 1, so we're doing nothing.",
                             self.name, milliseconds)
            return
        # todo also disable the timer which reenables this
        self.log.debug("Pulsing Driver for %sms", milliseconds)
        self.hw_driver.pulse(int(milliseconds))
        self.time_last_changed = time.time()
        self.time_when_done = self.time_last_changed + (milliseconds / 1000.0)

    def pwm(self, on_ms, off_ms, orig_on_ms=0):
        """Quickly turns this driver on and off to have the effect of holding
        this driver 'on' without burning up the coil.

        Args:
            on_ms: Integer of how long this driver is on in the 'on' portion.
            off_ms: Integer of how long this driver is off in the 'off'
                portion.
            orig_on_ms: Integer of how long this driver should be held on
                initially before the on/off pulsing starts.

        For example, to rapidly pulse a driver 1ms and then off 4ms, pass the
            values on_ms=1, off_ms=4.

        """
        self.log.debug("PWM Driver. initial pulse: %s, on: %s, off: %s",
                       orig_on_ms, on_ms, off_ms)
        self.hw_driver.pwm(on_ms, off_ms, orig_on_ms)
        self.time_last_changed = time.time()
        self.time_when_done = -1
        # todo also disable the timer which reenables this

    def timed_pwm(self, on_ms, off_ms, runtime_ms):
        """Quickly pulses a driver on/off for a specified number of
        milliseconds.

        Args:
            on_ms: Integer of how long this driver is on in the 'on' portion.
            off_ms: Integer of how long this driver is off in the 'off'
                portion.
            runtime_ms: Integer of the total number of milliseconds this driver
                should pulse on and off for.
        """
        self.log.debug("Timed PWM Driver. on: %s, off: %s, total ms: %s",
                       on_ms, off_ms, runtime_ms)
        self.hw_driver.pwm(on_ms, off_ms, runtime_ms)
        self.time_last_changed = time.time()
        self.time_when_done = -1
        # todo also disable the timer which reenables this



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
