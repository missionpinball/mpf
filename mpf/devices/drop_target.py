""" Contains the base classes for drop targets and drop target banks."""
# drop_target.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging

from mpf.devices.target import Target, TargetGroup


class DropTarget(Target):
    """Represents a single drop target in a pinball machine."""

    config_section = 'DropTargets'
    collection = 'drop_targets'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('DropTarget.' + name)
        super(DropTarget, self).__init__(machine, name, config, collection)

        self.device_str = 'droptarget'

        # set config defaults
        if 'reset_coil' not in self.config:
            self.config['reset_coil'] = None
        if 'knockdown_coil' not in self.config:
            self.config['knockdown_coil'] = None

        # can't read the switch until the switch controller is set up
        self.machine.events.add_handler('machine_init_phase1',
                                        self.update_state_from_switch)

        # todo add switch handler to watch for reset switch?
        # or do we? What about ball search? Config option?

    def update_state_from_switch(self):
        """Reads the state of the switch"""

        # set the initial complete state
        if self.machine.switch_controller.is_active(self.config['switch']):
            self.complete = True


class DropTargetBank(TargetGroup):
    """Represents a bank of drop targets in a pinball machine by grouping
    together multiple DropTarget class devices.
    """

    config_section = 'DropTargetBanks'
    collection = 'drop_target_banks'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('DropTargetBank.' + name)
        self.devices_str = 'drop_targets'
        self.member_collection = machine.drop_targets
        super(DropTargetBank, self).__init__(machine, name, config, collection)

        # set config defaults
        if 'reset_events' not in self.config:
            self.config['reset_events'] = None

        if 'reset_coils' in self.config:
            self.config['reset_coils'] = self.machine.string_to_list(
                                                self.config['reset_coils'])

        # can't read the switches until the switch controller is set up
        self.machine.events.add_handler('machine_init_phase1',
                                        self.update_count)

    def reset(self):
        super(DropTargetBank, self).reset()
        for coil in self.config['reset_coils']:
            self.machine.coils[coil].pulse()


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

