""" Contains the Switch parent class. """
# switch.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.device import Device
from mpf.system.timing import Timing


class Switch(Device):
    """ A switch in a pinball machine."""

    config_section = 'switches'
    collection = 'switches'
    class_label = 'switch'

    def __init__(self, machine, name, config, collection=None):
        config['number_str'] = str(config['number']).upper()
        super(Switch, self).__init__(machine, name, config, collection,
                                     platform_section='switches')

        self.machine = machine
        self.name = name
        self.deactivation_events = set()
        self.activation_events = set()
        self.state = 0
        """ The logical state of a switch. 1 = active, 0 = inactive. This takes
        into consideration the NC or NO settings for the switch."""
        self.hw_state = 0
        """ The physical hardware state of the switch. 1 = active,
        0 = inactive. This is what the actual hardware is reporting and does
        not consider whether a switch is NC or NO."""

        self.invert = 0

        self.recycle_ticks = 0
        self.recycle_clear_tick = 0
        self.recycle_jitter_count = 0

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_ticks = self.config['recycle_time']

        self.last_changed = None
        self.hw_timestamp = None

        self.log.debug("Creating '%s' with config: %s", name, self.config)

        self.hw_switch, self.number = (
            self.platform.configure_switch(self.config))

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
