""" Contains the base classes for Targets and TargetGroups."""
# target.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.show_controller import Playlist
from collections import deque


class Target(Device):
    '''
    Target:
        switch:
        light:
        reset_coils:
        reset_events:
            ball_starting: 0
            droptargetbank_Judge_complete: 1s
        complete_show:
        complete_script:

    '''

    # todo need to add complete show and complete script
    # todo support multiple switches & multiple lights

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Target.' + name)
        super(Target, self).__init__(machine, name, config, collection)

        self.complete = False
        self.lit = False
        self.device_str = 'target'

        # set config defaults
        if 'light' not in self.config:
            self.config['light'] = None

        # register for switch handlers so we know if this switch is hit
        self.machine.switch_controller.add_switch_handler(self.config['switch'],
                                                          self.hit)

    def hit(self, stealth=False):
        """This target was just hit.

        Stealth lets us change the status without posting the events. Used for
        rotation.
        """
        self.complete = True
        if self.config['light']:
            self.machine.lights[self.config['light']].on()
            # todo change this to the light controller, or to include an effect
            # todo only do this during active ball?

        if not stealth:
            self.machine.events.post(self.device_str + '_' + self.name +
                                     '_complete')

        # todo add lit handler

    def reset(self, stealth=False):
        """Resets this target."""
        self.complete = False
        if self.config['light']:
            self.machine.lights[self.config['light']].off()
            # todo change this to the light controller, or to include an effect
            # todo only do this during active ball?

        # todo do show or script


class TargetGroup(Device):
    """Represents a bank of drop targets in a pinball machine by grouping
    together multiple DropTarget class devices.

        targets:
        rotate_left_events:
        rotate_right_events:
        complete_show:
        complete_script:

    """

    # todo need to add complete_scripts
    # todo add show playback speed
    # need to add some concept of active that makes sure completion & rotations
    # only happen when they should

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('TargetGroup.' + name)
        super(TargetGroup, self).__init__(machine, name, config, collection)
        self.delay = DelayManager()

        #self.devices_str = 'targets'
        #self.member_collection

        self.num_complete = 0
        self.num_targets = 0
        self.targets = list()

        # make sure our target list is a list
        self.config[self.devices_str] = self.machine.string_to_list(
            self.config[self.devices_str])

        # create our list of objects
        for target in self.config[self.devices_str]:
            self.targets.append(self.member_collection[target])

        if 'complete_show' not in self.config:
            self.config['complete_show'] = None

        if 'complete_script' not in self.config:
            self.config['complete_script'] = None

        if 'rotate_left_events' not in self.config:
            self.config['rotate_left_events'] = list()
        else:
            self.config['rotate_left_events'] = self.machine.string_to_list(
                self.config['rotate_left_events'])

        if 'rotate_right_events' not in self.config:
            self.config['rotate_right_events'] = list()
        else:
            self.config['rotate_right_events'] = self.machine.string_to_list(
                self.config['rotate_right_events'])

        # If no reset events are specified, just self reset when complete
        if 'reset_events' not in self.config:
            self.config['reset_events'] = {(self.devices_str + '_' +
                                           self.name + '_complete'): 0}

        self.num_targets = len(self.targets)

        # set event handlers to watch for target state changes
        for target in self.targets:
            self.machine.events.add_handler(
                target.device_str + '_' + target.name + '_complete',
                self.update_count)
            self.machine.events.add_handler(
                target.device_str + '_' + target.name + '_reset',
                self.update_count)

        # need to wait until after the show controller is loaded
        self.machine.events.add_handler('machine_init_phase2', self.load_shows)

        # watch for rotation events
        for event in self.config['rotate_left_events']:
            self.machine.events.add_handler(event, self.rotate, direction='left')
        for event in self.config['rotate_right_events']:
            self.machine.events.add_handler(event, self.rotate, direction='right')

        self.enable_reset_events()

    def load_shows(self):
        if self.config['complete_show']:
            playlist = Playlist(self.machine)
            playlist.add_show(step_num=1,
                              show=self.machine.shows[self.config['complete_show']],
                              num_repeats=1,
                              tocks_per_sec=10)
            playlist.step_settings(step=1)
            self.config['complete_show'] = playlist

    def update_count(self):
        """One of this group's targets changed state. Let's recount them all."""

        num_complete = 0
        for target in self.targets:
            if target.complete:
                num_complete += 1

        self.num_complete = num_complete

        if self.num_complete == self.num_targets:
            self.group_complete()

    def group_complete(self):
        """All the targets in this group are complete."""

        if self.config['complete_show']:
            self.config['complete_show'].start(priority=100, repeat=False,
                                               reset=True)

        self.machine.events.post(self.devices_str + '_' +
                                 self.name + '_complete')

    def enable_reset_events(self):
        """Causes this target to watch for the reset events."""

        for event, delay in self.config['reset_events'].iteritems():
            self.machine.events.add_handler(event=event,
                                        handler=self.reset_request,
                                        ms_delay=Timing.string_to_ms(delay))

    def disable_reset_events(self):
        """Disables this target group watching for reset events. In other
        words, if the reset events are posted, this target group will not
        respond.
        """

        for event, delay in self.config['reset_events'].iteritems():
            self.machine.events.remove_handler(method=self.reset_request,
                                        ms_delay=(Timing.string_to_ms(delay)))

    def reset_request(self, ms_delay=0, **kwargs):
        """Received a request to reset this target group.

        This method will set a delay to wait for the amount of time specified
        in the reset delay, then call reset().

        **kwargs since we don't know where this is coming from

        """

        if ms_delay:
            self.delay.add(self.name + '_target_reset', ms_delay, self.reset)
        else:
            self.reset()

    def reset(self):
        """Resets this group of targets."""
        # todo only do this if we have completed targets? Add a force?
        self.log.debug("Resetting group")

        for target in self.targets:
            target.reset()

        self.num_complete = 0

        # todo do reset show or script

    def rotate(self, direction='right', steps=1):
        if self.num_complete == 0:
            return  # no need to go through all this if no targets are lit

        # create a list which shows which targets are active.
        complete_list = deque()
        for target in self.targets:
            if target.complete:
                complete_list.append(True)
            else:
                complete_list.append(False)

        # rotate that list
        if direction == 'right':
            complete_list.rotate(steps)
        else:
            complete_list.rotate(steps * -1)

        # step through all our targets and update their complete status
        for i in range(self.num_targets):
            if complete_list[i]:
                self.targets[i].hit(stealth=True)
            else:
                self.targets[i].reset(stealth=True)


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