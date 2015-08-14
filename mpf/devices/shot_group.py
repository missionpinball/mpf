""" Contains the ShotGroup base class."""
# shot_group.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import deque

from mpf.system.devices import Device
from mpf.system.config import Config


class ShotGroup(Device):
    """Represents a group of shots in a pinball machine by grouping
    together multiple `Shot` class devices. This is used so you get get
    "group-level" functionality, like shot rotation, shot group completion,
    etc. This would be used for a group of rollover lanes, a bank of standups,
    etc.

    """
    config_section = 'shot_groups'
    collection = 'shot_groups'
    class_label = 'shot_group'
    allow_per_mode_devices = True

    def __init__(self, machine, name, config, collection=None,
                 member_collection=None, device_str=None):
        self.log = logging.getLogger('ShotGroup.' + name)

        self.log.debug("Configuring shot group with settings: '%s'", config)

        super(ShotGroup, self).__init__(machine, name, config, collection)

        self.enabled = False

        if not device_str:
            self.device_str = 'shots'
        else:
            self.device_str = device_str

        if not member_collection:
            self.member_collection = self.machine.shots
        else:
            self.member_collection = member_collection

        self.shots = list()

        # make sure shot list is a Python list
        self.config[self.device_str] = Config.string_to_list(
            self.config[self.device_str])

        # convert shot list from str to objects
        for shot in self.config[self.device_str]:

            try:
                self.shots.append(self.member_collection[shot])
            except KeyError:
                self.log.error("No shot named '%s'. Could not add to group",
                               shot)

    def register_member_switches(self):
        for shot in self.config[self.device_str]:
            self.member_collection[shot].add_to_shot_group(self)

    def deregister_member_switches(self):
        for shot in self.config[self.device_str]:
            self.member_collection[shot].remove_from_shot_group(self)

    def remove_member_shot(self, shot):

        self.shots.remove(shot)
        self.deregister_member_switches()
        self.register_member_switches()

    def hit(self, profile_name, profile_step_name, **kwargs):
        """One of the member shots in this shot group was hit.

        This method is only processed if this shot group is enabled.

        Args:
            profile_name: String name of the active profile of the shot that
                was hit.
            profile_step_name: String name of the step name of the profile of
                the shot that was hit.

        """
        if self.enabled:
            self.machine.events.post(self.name + '_' + profile_name + '_' +
                                     profile_step_name + '_hit')

    def enable(self, **kwargs):
        """Enables this shot group. Also enables all the shots in this
        group.

        """

        if self.enabled:
            return

        self.enabled = True

        self.register_member_switches()

        for shot in self.shots:
            shot.enable()

    def disable(self, **kwargs):
        """Disables this shot group. Also disables all the shots in this
        group.

        """

        if not self.enabled:
            return

        self.deregister_member_switches()

        for shot in self.shots:
            shot.disable()

        self.enabled = False

    def reset(self, **kwargs):
        """Resets each of the shots in this group back to the initial step in
        whatever shot profile they have applied. This is the same as calling
        each shot's reset() method one-by-one.

        """
        for shot in self.shots:
            shot.reset()

    def remove_profile(self, **kwargs):
        """Removes the current active profile from every shot in the group.

        """
        for shot in self.shots:
            shot.remove_active_profile()

    def advance(self, **kwargs):
        """Advances the current active profile from every shot in the group
        one step forward.

        """
        for shot in self.shots:
            shot.advance()

    def rotate(self, direction='right', steps=1, states=None,
               exclude_states=None, **kwargs):
        """Rotates (or "shifts") the state of all the shots in this group.
        This is used for things like lane change, where hitting the flipper
        button shifts all the states of the shots in the group to the left or
        right.

        This method actually transfers the current state of each shot profile
        to the left or the right, and the shot on the end rolls over to the
        taret on the other end.

        Args:
            direction: String that specifies whether the rotation direction is
                to the left or right. Values are 'right' or 'left'. Default is
                'right'.
            steps: Integer of how many steps you want to rotate. Default is 1.
            states: A string of a state or a list of strings that represent the
                targets that will be selected to rotate. If None (default), then
                all targets will be included.
            exclude_states: A string of a state or a list of strings that
                controls whether any targets will *not* be rotated. (Any
                targets with an active profile in one of these states will not
                be included in the rotation. Default is None which means all
                targets will be rotated)
        """

        if not self.enabled:
            return

        # if we don't have states or exclude_states, we'll see if the first shot
        # in the group has them and use those. Since all the shots should have
        # the same profile applied, it's ok to just pick from the first one.

        if states:
            states = Config.string_to_lowercase_list(states)
        else:
            states = self.shots[0].active_profile['step_names_to_rotate']

        if exclude_states:
            exclude_states = Config.string_to_lowercase_list(exclude_states)
        else:
            exclude_states = (
                self.shots[0].active_profile['step_names_to_not_rotate'])

        shot_list = list()

        # build of a list of shots we're actually going to rotate
        for shot in self.shots:
            if ((not states or shot.current_step_name in states) and
                    shot.current_step_name not in exclude_states):

                shot_list.append(shot)

        shot_state_list = deque()

        for shot in shot_list:

            try:
                current_step = shot.running_light_show.current_location

            except AttributeError:
                current_step = -1

            shot_state_list.append(
                (shot.player[shot.player_variable], current_step)
                                    )

        # rotate that list
        if direction == 'right':
            shot_state_list.rotate(steps)
        else:
            shot_state_list.rotate(steps * -1)

        # step through all our shots and update their complete status
        for i in range(len(shot_list)):
            shot_list[i].jump(step=shot_state_list[i][0],
                              update_group=False,
                              current_show_step=shot_state_list[i][1])

    def rotate_right(self, steps=1, **kwargs):
        """Rotates the state of the shots to the right. This method is the
        same as calling rotate('right', steps)

        Args:
            steps: Integer of how many steps you want to rotate. Default is 1.

        """
        self.rotate(direction='right', steps=steps)

    def rotate_left(self, steps=1, **kwargs):
        """Rotates the state of the shots to the left. This method is the
        same as calling rotate('left', steps)

        Args:
            steps: Integer of how many steps you want to rotate. Default is 1.

        """
        self.rotate(direction='left', steps=steps)

    def check_for_complete(self):
        """Checks all the shots in this shot group. If they are all in the
        same step, then that step number is returned. If they are in different
        steps, False is returned.

        """

        shot_states = set()

        for shot in self.shots:
            shot_states.add(shot.current_step_name)

        # <name>_<profile>_<step>
        if len(shot_states) == 1 and shot_states.pop():
            self.machine.events.post(self.name + '_' +
                                     self.shots[0].active_profile_name + '_' +
                                     self.shots[0].current_step_name +
                                     '_complete')

    def device_added_to_mode(self, player):
        self.enable()

    def remove(self):
        self.log.debug("Removing...")
        self.deregister_member_switches()
        del self.machine.shot_groups[self.name]


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
