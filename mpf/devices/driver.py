""" Contains the Driver parent class. """
# driver.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import time
from mpf.system.device import Device


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

    config_section = 'coils'
    collection = 'coils'
    class_label = 'coil'

    def __init__(self, machine, name, config, collection=None, validate=True):
        config['number_str'] = str(config['number']).upper()
        super(Driver, self).__init__(machine, name, config, collection,
                                     platform_section='coils',
                                     validate=validate)

        self.time_last_changed = 0
        self.hw_driver, self.number = (self.platform.configure_driver(self.config))

    def validate_driver_settings(self, **kwargs):
        return self.hw_driver.validate_driver_settings(**kwargs)

    def enable(self, **kwargs):
        """Enables a driver by holding it 'on'.

        If this driver is configured with a holdpatter, then this method will use
        that holdpatter to pwm pulse the driver.

        If not, then this method will just enable the driver. As a safety
        precaution, if you want to enable() this driver without pwm, then you
        have to add the following option to this driver in your machine
        configuration files:

        allow_enable: True
        """

        if self.config['allow_enable']:
            self.time_last_changed = time.time()
            self.log.debug("Enabling Driver")
            self.hw_driver.enable()
        else:
            self.log.warning("Received a command to enable this coil without "
                             "pwm, but 'allow_enable' has not been set to True"
                             " in this coil's configuration.")

    def disable(self, **kwargs):
        """ Disables this driver """
        self.log.debug("Disabling Driver")
        self.time_last_changed = time.time()
        self.hw_driver.disable()
        # todo also disable the timer which reenables this

    def pulse(self, milliseconds=None, power=1.0, **kwargs):
        """ Pulses this driver.

        Args:
            milliseconds: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            power: A multiplier that will be applied to the default pulse time,
                typically a float between 0.0 and 1.0. (Note this is only used
                if milliseconds is not specified.)
        """

        self.log.debug("Pulsing Driver. Overriding default pulse_ms with: "
                       "%sms", milliseconds)
        self.time_last_changed = time.time()
        self.hw_driver.pulse(milliseconds)




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
