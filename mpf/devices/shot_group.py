""" Contains the ShotGroup base class."""
# shot_group.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from collections import deque

from mpf.system.device import Device
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

    def __init__(self, machine, name, config, collection=None,
                 member_collection=None, device_str=None):

        self.shots = list()  # list of strings

        for shot in Config.string_to_list(config['shots']):
            self.shots.append(machine.shots[shot])

        super(ShotGroup, self).__init__(machine, name, config, collection)

        self.enabled = False
        self.rotation_enabled = True

        if self.debug:
            self._enable_related_device_debugging()

    def _enable_related_device_debugging(self):

        self.log.debug("Enabling debugging for this shot groups's member shots")

        for shot in self.shots:
            shot.enable_debugging()

    def _disable_related_device_debugging(self):
        for shot in self.shots:
            shot.disable_debugging()

    def _watch_member_shots(self):
        for shot in self.shots:
            self.machine.events.add_handler(shot.name + '_hit', self.hit)

    def _stop_watching_member_shots(self):
        # remove the hit events
        self.machine.events.remove_handler(self.hit)

    def hit(self, profile, state, **kwargs):
        """One of the member shots in this shot group was hit.

        Args:
            profile: String name of the active profile of the shot that
                was hit.
            profile: String name of the state name of the profile of
                the shot that was hit.

        """
        if self.debug:
            self.log.debug('Hit! Active profile: %s, Current state: %s',
                           profile_name, profile_state_name)

        self.machine.events.post(self.name + '_hit',
                                 profile=profile, state=state)

        self.machine.events.post(self.name + '_' + profile + '_hit',
                                 profile=profile, state=state)

        self.machine.events.post(self.name + '_' + profile + '_' + state +
                                 '_hit', profile=profile, state=state)

        self.check_for_complete()

    def enable(self, **kwargs):
        """Enables this shot group. Also enables all the shots in this
        group.

        """

        if self.enabled:
            return

        if self.debug:
            self.log.debug('Enabling')

        self.enabled = True

        self._watch_member_shots()

        for shot in self.shots:
            shot.enable()

    def disable(self, **kwargs):
        """Disables this shot group. Also disables all the shots in this
        group.

        """

        if not self.enabled:
            return

        if self.debug:
            self.log.debug('Disabling')

        self._stop_watching_member_shots()

        for shot in self.shots:
            shot.disable()

        self.enabled = False

    def enable_rotation(self, **kwargs):
        """Enables shot rotation. If disabled, rotation events do not actually
        rotate the shots.

        """
        if self.debug:
            self.log.debug('Enabling rotation')
        self.rotation_enabled = True

    def disable_rotation(self, **kwargs):
        """Disables shot rotation. If disabled, rotation events do not actually
        rotate the shots.

        """
        if self.debug:
            self.log.debug('Disabling rotation')
        self.rotation_enabled = False

    def reset(self, **kwargs):
        """Resets each of the shots in this group back to the initial state in
        whatever shot profile they have applied. This is the same as calling
        each shot's reset() method one-by-one.

        """
        if self.debug:
            self.log.debug('Resetting')
        for shot in self.shots:
            shot.reset()

    def apply_profile(self, profile, priority):
        if profile in self.machine.shot_profile_manager.profiles:
            if self.debug:
                self.log.debug("Applying shot profile '%s', priority %s",
                               profile, priority)

            profile_tuple = (profile, priority,
                self.machine.shot_profile_manager.profiles[profile],
                self)

            if profile_tuple not in self.profiles:
                self.profiles.append(profile_tuple)

            for shot in self.shots:
                shot.apply_profile(profile, priority, self)

            self._sort_profiles()

        else:
            if not self.active_profile:
                self.apply_profile('default', priority)

            if self.debug:
                self.log.debug("Shot profile '%s' not found. Shot is has '%s' "
                               "applied.", profile, self.active_profile_name)

    def _sort_profiles(self):
        self.profiles.sort(key=lambda x: x[1], reverse=True)

        (self.active_profile_name,
         self.active_profile_priority,
         self.active_profile_settings,
         _) = self.profiles[0]

    def remove_active_profile(self, **kwargs):
        """Removes the current active profile from every shot in the group.

        """
        if self.debug:
            self.log.debug('Removing active profile')
        for shot in self.shots:
            shot.remove_active_profile()

    def advance(self, **kwargs):
        """Advances the current active profile from every shot in the group
        one step forward.

        """
        if self.debug:
            self.log.debug('Advancing')
        for shot in self.shots:
            shot.advance()

    def rotate(self, direction=None, steps=1, states=None,
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
                to the left or right. Values are 'right' or 'left'. Default of
                None will cause the shot group to rotate in the direction as
                specified by the rotation_pattern.
            steps: Integer of how many steps you want to rotate. Default is 1.
            states: A string of a state or a list of strings that represent the
                targets that will be selected to rotate. If None (default), then
                all targets will be included.
            exclude_states: A string of a state or a list of strings that
                controls whether any targets will *not* be rotated. (Any
                targets with an active profile in one of these states will not
                be included in the rotation. Default is None which means all
                targets will be rotated)

        Note that this shot group must, and rotation_events for this
        shot group, must both be enabled for the rotation events to work.

        """

        if not self.enabled or not self.rotation_enabled:

            if self.debug:
                self.log.debug("Received rotation request. Shot group enabled:"
                               "%s, Rotation Enabled: %s. Will NOT rotate",
                               self.enabled, self.rotation_enabled)

            return

        # if we don't have states or exclude_states, we'll see if the first shot
        # in the group has them and use those. Since all the shots should have
        # the same profile applied, it's ok to just pick from the first one.

        if states:
            states = Config.string_to_lowercase_list(states)
        else:
            states = self.shots[0].active_profile['state_names_to_rotate']

        if exclude_states:
            exclude_states = Config.string_to_lowercase_list(exclude_states)
        else:
            exclude_states = (
                self.shots[0].active_profile['state_names_to_not_rotate'])

        shot_list = list()

        # build of a list of shots we're actually going to rotate
        for shot in self.shots:
            if ((not states or shot.current_state_name in states) and
                    shot.current_state_name not in exclude_states):

                shot_list.append(shot)

        shot_state_list = deque()

        for shot in shot_list:

            try:
                current_state = shot.running_light_show.current_location

            except AttributeError:
                current_state = -1

            shot_state_list.append(
                (shot.player[shot.player_variable], current_state)
                                    )

        if self.debug:
            self.log.debug('Rotating. Direction: %s, Include states: %s, '
                           'Exclude states: %s, Shots to be rotated: %s',
                           direction, states,
               exclude_states, [x.name for x in shot_list])

            for shot in shot_list:
                shot.log.debug("This shot is part of a rotation event")


        # figure out which direction we're going to rotate
        if not direction:
            direction = self.rotation_pattern[0]
            self.rotation_pattern.rotate(-1)

            if self.debug:
                self.log.debug("Since no direction was specified, pulling from"
                               " rotation pattern: '%s'", direction)

        # rotate that list
        if direction == 'right':
            shot_state_list.rotate(steps)
        else:
            shot_state_list.rotate(steps * -1)

        # step through all our shots and update their states
        for i in range(len(shot_list)):
            shot_list[i].jump(state=shot_state_list[i][0],
                              lightshow_step=shot_state_list[i][1])

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
        same state, then a complete event is posted.

        """
        shot_states = set()

        for shot in self.shots:
            shot_states.add(shot.current_state_name)

        # <name>_<profile>_<state>
        if len(shot_states) == 1 and shot_states.pop():
            self.machine.events.post(self.name + '_' +
                                     self.shots[0].active_profile_name + '_' +
                                     self.shots[0].current_state_name +
                                     '_complete')

    def device_added_to_mode(self, player):
        if 'enable_events' not in self.config:
            self.enable()

    def remove(self):
        if self.debug:
            self.log.debug("Removing this shot group")
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
