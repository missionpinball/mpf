""" Contains the base classes for drop targets and drop target banks."""
# drop_target.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

from mpf.devices.target import Target, TargetGroup
from mpf.system.config import Config


class DropTarget(Target):
    """Represents a single drop target in a pinball machine.

    Args: Same as the `Target` parent class"""

    config_section = 'drop_targets'
    collection = 'drop_targets'
    class_label = 'drop_target'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('DropTarget.' + name)
        self.device_str = 'droptarget'

        super(DropTarget, self).__init__(machine, name, config, collection)

        if self.config['profile'] == 'default':
            self.config['profile'] = 'drop_target_default'

        # Drop targets maintain self.complete in addition to self.lit from the
        # parent class since they can maintain a physical state which could
        # vary from the lit state. For example, you might want to have a drop
        # target "lit" that was still standing (i.e. not complete)
        self.complete = False
        self.reset_coil = None
        self.knockdown_coil = None

        if 'reset_coil' in self.config:
            self.reset_coil = self.machine.coils[self.config['reset_coil']]

        if 'knockdown_coil' in self.config:
            self.knockdown_coil = self.machine.coils[self.config['knockdown_coil']]

        # can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_3',
                                        self.update_state_from_switch)

    def _register_switch_handlers(self):
        # register for notification of switch state
        # this is in addition to the parent since drop targets track
        # self.complete in separately

        self.machine.switch_controller.add_switch_handler(self.config['switch'][0],
            self.update_state_from_switch, 0)
        self.machine.switch_controller.add_switch_handler(self.config['switch'][0],
            self.update_state_from_switch, 1)

    def knockdown(self, **kwargs):
        """Pulses the knockdown coil to knock down this drop target."""
        if self.knockdown_coil:
            self.knockdown_coil.pulse()

    def update_state_from_switch(self):
        """Reads the state of this drop target's switch and updates this drop
        target's "complete" status.

        If this method sees that this target has changed back to its up state,
        then it will also reset the target profile back to its first step.

        """

        print "dt switch change"

        # set the initial complete state
        if self.machine.switch_controller.is_active(self.config['switch'][0]):
            print "dt now complete"
            self.complete = True
            self.hit()
        else:
            print 'dt now incomplete'
            self.complete = False
            self.jump(step=0)

    def reset(self, **kwargs):
        """Resets this drop target.

        If this drop target is configured with a reset coil, then this method
        will pulse that coil. If not, then it checks to see if this drop target
        is part of a drop target bank, and if so, it calls the reset() method of
        the drop target bank.

        This method does not reset the target profile, however, the switch event
        handler should reset the target profile on its own when the drop target
        physically moves back to the up position.

        """

        if self.target_group:
            #self.target_group.reset()
            pass
        elif self.reset_coil:
            self.reset_coil.pulse()


class DropTargetBank(TargetGroup):
    """Represents a bank of drop targets in a pinball machine by grouping
    together multiple `DropTarget` class devices.

    """
    config_section = 'drop_target_banks'
    collection = 'drop_target_banks'
    class_label = 'drop_target_bank'

    def __init__(self, machine, name, config, collection,
                 member_collection=None, device_str=None):

        self.device_str = 'drop_targets'

        self.log = logging.getLogger('DropTargetBank.' + name)
        super(DropTargetBank, self).__init__(machine, name, config, collection,
                                             machine.drop_targets,
                                             self.device_str)

        self.reset_coil = None
        self.reset_coils = set()

        if 'reset_coils' in self.config:
            for coil_name in Config.string_to_list(self.config['reset_coils']):
                self.reset_coils.add(self.machine.coils[coil_name])

        if 'reset_coil' in self.config:
            self.reset_coil = self.machine.coils[self.config['reset_coil']]

    def reset(self, **kwargs):
        """Resets this bank of drop targets.

        This method has some intelligence to figure out what coil(s) it should
        fire. It builds up a set by looking at its own reset_coil and
        reset_coils settings, and also scanning through all the member drop
        targets and collecting their coils. Then it pulses each of them. (This
        coil list is a "set" which means it only sends a single pulse to each
        coil, even if each drop target is configured with its own coil.)

        """
        # figure out all the coils we need to pulse
        coils = set()

        for drop_target in self.targets:
            if drop_target.reset_coil:
                coils.add(drop_target.reset_coil)

        for coil in self.reset_coils:
            coils.add(coil)

        if self.reset_coil:
            coils.add(self.reset_coil)

        # now pulse them
        for coil in coils:
            coil.pulse()


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
