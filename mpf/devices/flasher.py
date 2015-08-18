""" Contains the Flasher parent class. """
# flasher.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.device import Device


class Flasher(Device):
    """Generic class that holds flasher objects.
    """

    config_section = 'flashers'
    collection = 'flashers'
    class_label = 'flasher'

    def __init__(self, machine, name, config, collection=None):
        config['number_str'] = str(config['number']).upper()
        super(Flasher, self).__init__(machine, name, config, collection,
                                      platform_section='flashers')

        self.hw_driver, self.number = (
            self.platform.configure_driver(config=self.config,
                                           device_type='flasher'))

        if self.config['flash_ms'] is None:
            self.config['flash_ms'] = (
                self.machine.config['mpf']['default_flash_ms'])

    def flash(self, milliseconds=None):
        """Flashes the flasher.

        Args:
            milliseconds: Int of how long you want the flash to be, in ms.
                Default is None which causes the flasher to flash for whatever
                its default config is, either its own flash_ms or the system-
                wide default_flash_ms settings. (Current default is 50ms.)

        """

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
