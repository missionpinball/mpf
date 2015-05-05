""" Contains the Flasher parent class. """
# flasher.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device


class Flasher(Device):
    """Generic class that holds flasher objects.
    """

    config_section = 'flashers'
    collection = 'flashers'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Flasher.' + name)
        super(Flasher, self).__init__(machine, name, config, collection,
                                      platform_section='flashers')

        # We save out number_str since the platform driver will convert the
        # number into a hardware number, but we need the original number for
        # some things later.
        self.config['number_str'] = str(config['number']).upper()

        self.hw_driver, self.number = (
            self.platform.configure_driver(self.config))
        self.log.debug("Creating '%s' with config: %s", name, config)

        if 'flash_ms' not in self.config:
            self.config['flash_ms'] = 10

    def flash(self, milliseconds=None):

        if milliseconds is None:
            milliseconds = self.config['flash_ms']

        self.hw_driver.pulse(int(milliseconds))

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
