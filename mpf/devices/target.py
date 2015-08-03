""" Contains the base classes for Targets and TargetGroups."""
# target.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import deque

from mpf.system.devices import Device
from mpf.system.config import Config


class Target(Device):

    config_section = 'targets'
    collection = 'targets'
    class_label = 'target'

    def __init__(self, machine, name, config, collection=None):
        """Represents a target in a pinball machine. A target is typically the
        combination of a switch and a light, such as a standup or rollover.
        Targets have multiple 'states' and intelligence to track what state the
        target was in when it was hit and to advance through various states as
        it's hit again and again.

        """
        self.log = logging.getLogger('Target.' + name)
        self.log.debug("Configuring target with settings: '%s'", config)

        super(Target, self).__init__(machine, name, config, collection)

        self.active_profile_name = None
        self.active_profile_config = dict()
        self.active_profile_steps = list()
        self.active_profile_priority = 0
        self.current_step_index = 0
        self.current_step_name = None
        self.running_light_show = None
        self.target_group = None
        self.profiles = list()
        self.player = None
        self.player_variable = None

        self.enabled = False

        if 'profile' not in self.config:
            self.config['profile'] = 'default'

        if 'switch' in self.config:
            self.config['switch'] = Config.string_to_list(self.config['switch'])
        else:
            self.config['switch'] = list()

        if 'light' in self.config:
            self.config['light'] = Config.string_to_list(self.config['light'])
        else:
            self.config['light'] = list()

        if 'led' in self.config:
            self.config['led'] = Config.string_to_list(self.config['led'])
        else:
            self.config['led'] = list()

        self.machine.events.add_handler('init_phase_3',
                                        self._register_switch_handlers)

    def _set_player_variable(self):
        if 'player_variable' in self.active_profile_settings:
            self.player_variable = self.active_profile_settings['player_variable']
        else:
            self.player_variable = (self.name + '_' + self.active_profile_name)

    def _register_switch_handlers(self):
        for switch in self.config['switch']:
            self.machine.switch_controller.add_switch_handler(
                switch, self.hit, 1)

    def _advance_step(self, steps=1):
        if (self.player[self.player_variable] + 1 >=
                len(self.active_profile_steps)):
            if self.config['loops']:
                self.player[self.player_variable] = 0
            else:
                return
        else:
            self.machine.game.player[self.player_variable] += 1

        self._stop_current_lights()
        self._update_current_step_variables()
        self._do_step_actions()
        self._update_group_status()

    def _update_group_status(self):
        if self.target_group:
            self.target_group.check_for_complete()

    def _stop_current_lights(self):
        if self.running_light_show:
            self.running_light_show.stop()
            self.running_light_show = None

    def _update_current_step_variables(self):
        self.current_step_index = self.player[self.player_variable]

        self.current_step_name = (
            self.active_profile_steps[self.current_step_index]['name'])

    def _do_step_actions(self, ):
        if ('light_script' in self.active_profile_steps[self.current_step_index]
                and (self.config['light'] or self.config['led'])):

            new_show = self.machine.light_controller.run_registered_script(
                self.active_profile_steps[self.current_step_index]['light_script'],
                lights=self.config['light'], leds=self.config['led'],
                priority=self.profiles[0][1])

            if new_show:
                self.running_light_show = new_show

            else:
                self.log.warning("Error running light_script '%s'",
                    self.active_profile_steps[self.current_step_index]['light_script'])
                self.running_light_show = None

        else:
            self.running_light_show = None

    def _update_lights(self):
        if ('light_script' in self.active_profile_steps[self.current_step_index]
                and ((self.running_light_show and
                      self.running_light_show.priority <= self.active_profile_priority)
                    or not self.running_light_show)):

            self.running_light_show = (
                self.machine.light_controller.run_registered_script(
                self.active_profile_steps[self.current_step_index]['light_script'],
                lights=self.config['light'], leds=self.config['leds'],
                start_location=-1, priority=self.active_profile_priority,
                **self.active_profile_steps[self.current_step_index]))

    def player_turn_start(self, player):
        """Called when a player's turn starts to update the player reference to
        the current player and to apply the default machine-wide target profile.

        """
        self.player = player
        self.apply_profile(self.config['profile'], priority=0)

    def apply_profile(self, profile, priority, removal_key=None):
        """Applies a target profile to this target.

        Args:
            profile: String name of the profile to apply.
            priority: Priority of this profile. Only one profile is active at a
                time. If this profile is the highest, then it will be active. If
                not then it will still be applied and will become active if
                higher priority profiles are removed.
            removal_key: Optional hashable that can be used to identify this
                profile so it can be removed later.

        """
        if profile in self.machine.target_controller.profiles:
            self.log.info("Applying target profile '%s', priority %s", profile,
                          priority)

            profile_tuple = (profile, priority,
                self.machine.target_controller.profiles[profile],
                self.machine.target_controller.profiles[profile]['steps'],
                removal_key)

            self.profiles.append(profile_tuple)

            self._sort_profiles()
            self._set_player_variable()
            self._update_current_step_variables()
            self._update_lights()

        else:
            if not self.active_profile_name:
                self.apply_profile('default')

            self.log.info("Target profile '%s' not found. Target is has '%s' "
                           "applied.", profile, self.active_profile_name)

    def remove_profile(self, removal_key):
        """Removes a target profile from this target.

        If the profile removed is the active one (because it was the highest
        priority), then this method activates the next-highest priority profile.

        Args:
            removal_key: The key that was returned when the profile was applied
                to the target which is how the profile you want to remove is
                identified.

        """
        old_profile = self.active_profile_name

        for entry in self.profiles[:]:  # slice so we can remove while iter
            if entry[4] == removal_key:
                self.profiles.remove(entry)

        self._sort_profiles()

        if self.active_profile_name != old_profile:
            self.running_light_show.stop()
            self.running_light_show = None
            self._set_player_variable()
            self._update_current_step_variables()
            self._update_lights()

    def _sort_profiles(self):
        self.profiles.sort(key=lambda x: x[1], reverse=True)

        (self.active_profile_name, self.active_profile_priority,
         self.active_profile_settings,
         self.active_profile_steps, _) = self.profiles[0]

    def hit(self, force=False, **kwargs):
        """Method which is called to indicate this target was just hit. This
        method will advance the currently-active target profile.

        Args:
            force: Boolean that forces this hit to be registered. Default is
                False which means if there are no balls in play (e.g. after a
                tilt) then this hit isn't processed. Set this to True if you
                want to force the hit to be processed even if no balls are in
                play.

        Note that the target must be enabled in order for this hit to be
        processed.

        """

        if (not self.machine.game or (
                self.machine.game and not self.machine.game.balls_in_play) and
                not force):
            return

        if not self.enabled:
            return

        self.log.info("Hit! Profile: %s, Current Step: %s",
                      self.active_profile_name, self.current_step_name)

        # post event <name>_<profile>_<step>_hit
        self.machine.events.post(self.name + '_' +
                                 self.active_profile_name + '_' +
                                 self.current_step_name + '_hit')

        self._advance_step()

    def jump(self, step, update_group=True):
        """Jumps to a certain step in the active target profile.

        Args:
            step: int of the step number you want to jump to. Note that steps
                are zero-based, so the first step is 0.
            update_group: Boolean which controls whether this jump event should
                also contact the target group this target belongs to to see if
                it should update this group's complete status. Default is True.
                False is used for things like target rotation where a target
                needs to jump to a new position but you don't want to post the
                group complete events again.

        """

        if not self.machine.game:
            return

        self._stop_current_lights()
        self.player[self.player_variable] = step
        self._update_current_step_variables()  # curr_step_index, curr_step_name

        if update_group:
            self._update_group_status()

        self._update_lights()

    def enable(self, **kwargs):
        """Enables this target. If the target is not enabled, hits to it will
        not be processed.

        """
        self.log.info("Enabling...")
        self.enabled = True

    def disable(self, **kwargs):
        """Disables this target. If the target is not enabled, hits to it will
        not be processed.

        """
        self.log.info("Disabling...")
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the active target profile back to the first step (Step 0).
        This method is the same as calling jump(0).

        """
        self.jump(step=0)


class TargetGroup(Device):
    """Represents a group of targets in a pinball machine by grouping
    together multiple `Target` class devices. This is used so you get get
    "group-level" functionality, like target rotation, target group completion,
    etc. This would be used for a group of rollover lanes, a bank of standups,
    etc.

    """
    config_section = 'target_groups'
    collection = 'target_groups'
    class_label = 'target_group'

    def __init__(self, machine, name, config, collection=None,
                 member_collection=None, device_str=None):
        self.log = logging.getLogger('TargetGroup.' + name)

        self.log.debug("Configuring target group with settings: '%s'", config)

        super(TargetGroup, self).__init__(machine, name, config, collection)

        self.enabled = False

        if not device_str:
            self.device_str = 'targets'
        else:
            self.device_str = device_str

        if not member_collection:
            member_collection = self.machine.targets

        self.targets = list()

        # make sure target list is a Python list
        self.config[self.device_str] = Config.string_to_list(
            self.config[self.device_str])

        # convert target list from str to objects
        for target in self.config[self.device_str]:
            self.targets.append(member_collection[target])
            member_collection[target].target_group = self

        self.machine.events.add_handler('init_phase_3',
                                        self._register_switch_handlers)

    def _register_switch_handlers(self):
        for target in self.targets:
            for switch in target.config['switch']:
                self.machine.switch_controller.add_switch_handler(
                    switch, self.hit, 1)

    def hit(self, **kwargs):
        """One of the member targets in this target group was hit.

        This method is only processed if this target group is enabled.

        """
        if self.enabled:
            self.machine.events.post(self.name + '_hit')

    def enable(self, **kwargs):
        """Enables this target group. Also enables all the targets in this
        group.

        """
        self.enabled = True

        for target in self.targets:
            target.enable()

    def disable(self, **kwargs):
        """Disables this target group. Also disables all the targets in this
        group.

        """
        for target in self.targets:
            target.disable()

        self.enabled = False

    def reset(self, **kwargs):
        """Resets each of the targets in this group back to the initial step in
        whatever target profile they have applied. This is the same as calling
        each target's reset() method one-by-one.

        """
        for target in self.targets:
            target.reset()

    def rotate(self, direction='right', steps=1, **kwargs):
        """Rotates (or "shifts") the state of all the targets in this group.
        This is used for things like lane change, where hitting the flipper
        button shifts all the states of the targets in the group to the left or
        right.

        This method actually transfers the current state of each target profile
        to the left or the right, and the target on the end rolls over to the
        taret on the other end.

        Args:
            direction: String that specifies whether the rotation direction is
                to the left or right. Values are 'right' or 'left'. Default is
                'right'.
            steps: Integer of how many steps you want to rotate. Default is 1.

        """

        if not self.enabled:
            return

        target_state_list = deque()

        for target in self.targets:
            target_state_list.append(target.player[target.player_variable])

        # rotate that list
        if direction == 'right':
            target_state_list.rotate(steps)
        else:
            target_state_list.rotate(steps * -1)

        # step through all our targets and update their complete status
        for i in range(len(self.targets)):
            self.targets[i].jump(step=target_state_list[i], update_group=False)

    def rotate_right(self, steps=1, **kwargs):
        """Rotates the state of the targets to the right. This method is the
        same as calling rotate('right', steps)

        Args:
            steps: Integer of how many steps you want to rotate. Default is 1.

        """
        self.rotate(direction='right', steps=steps)

    def rotate_left(self, steps=1, **kwargs):
        """Rotates the state of the targets to the left. This method is the
        same as calling rotate('left', steps)

        Args:
            steps: Integer of how many steps you want to rotate. Default is 1.

        """
        self.rotate(direction='left', steps=steps)

    def check_for_complete(self):
        """Checks all the targets in this target group. If they are all in the
        same step, then that step number is returned. If they are in different
        steps, False is returned.

        """

        target_states = set()

        for target in self.targets:
            target_states.add(target.current_step_name)

        # <name>_<profile>_<step>
        if len(target_states) == 1 and target_states.pop():
            self.machine.events.post(self.name + '_' +
                                     self.targets[0].active_profile_name + '_' +
                                     self.targets[0].current_step_name +
                                     '_complete')


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
