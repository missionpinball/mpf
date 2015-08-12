""" Contains the base classes for Shots and ShotGroups."""
# shot.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import deque

from mpf.system.devices import Device
from mpf.system.config import Config
from mpf.system.timing import Timing


class Shot(Device):

    config_section = 'shots'
    collection = 'shots'
    class_label = 'shot'
    allow_per_mode_devices = True

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track shots.
    """

    def __init__(self, machine, name, config, collection=None):
        """Represents a shot in a pinball machine. A shot is typically the
        combination of a switch and a light, such as a standup or rollover.
        Shots have multiple 'states' and intelligence to track what state the
        shot was in when it was hit and to advance through various states as
        it's hit again and again.

        """
        self.log = logging.getLogger('Shot.' + name)
        self.log.debug("Configuring shot with settings: '%s'", config)

        super(Shot, self).__init__(machine, name, config, collection)

        self.active_profile_name = None
        self.active_profile_config = dict()
        self.active_profile_steps = list()
        self.active_profile_priority = 0
        self.current_step_index = 0
        self.current_step_name = None
        self.running_light_show = None
        self.shot_groups = set()
        self.profiles = list()
        self.player_variable = None
        self.sequence_index = 0
        self.sequence_delay = False
        self.player = None

        self.enabled = False

        if 'profile' not in self.config:
            self.config['profile'] = 'default'

        if 'switch' in self.config:
            self.config['switch'] = Config.string_to_list(self.config['switch'])
        else:
            self.config['switch'] = list()

        if 'switch_sequence' in self.config:
            self.config['switch_sequence'] = (
                Config.string_to_list(self.config['switch_sequence']))
        else:
            self.config['switch_sequence'] = list()

        if 'time' in self.config:
            self.config['time'] = Timing.string_to_ms(self.config['time'])
        else:
            self.config['time'] = 0

        if 'light' in self.config:
            self.config['light'] = Config.string_to_list(self.config['light'])
        else:
            self.config['light'] = list()

        if 'led' in self.config:
            self.config['led'] = Config.string_to_list(self.config['led'])
        else:
            self.config['led'] = list()

    def _set_player_variable(self):
        if 'player_variable' in self.active_profile_settings:
            self.player_variable = self.active_profile_settings['player_variable']
        else:
            self.player_variable = (self.name + '_' + self.active_profile_name)

    def _register_switch_handlers(self):
        for switch in self.config['switch']:
            self.machine.switch_controller.add_switch_handler(
                switch, self.hit, 1)

        for switch in self.config['switch_sequence']:
            self.machine.switch_controller.add_switch_handler(
                switch, self._sequence_hit, 1, return_info=True)

    def _remove_switch_handlers(self):
        for switch in self.config['switch']:
            self.machine.switch_controller.remove_switch_handler(
                switch, self.hit, 1)

        for switch in self.config['switch_sequence']:
            self.machine.switch_controller.remove_switch_handler(
                switch, self._sequence_hit, 1)

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

        for group in self.shot_groups:
            group.check_for_complete()

    def _stop_current_lights(self):

        try:
            self.running_light_show.stop(hold=False, reset=False)
        except AttributeError:
            pass

        self.running_light_show = None

    def _update_current_step_variables(self):
        self.current_step_index = self.player[self.player_variable]

        self.current_step_name = (
            self.active_profile_steps[self.current_step_index]['name'])

    def _do_step_actions(self, ):
        if ('light_script' in self.active_profile_steps[self.current_step_index]
                and (self.config['light'] or self.config['led'])):

            settings = self.active_profile_steps[self.current_step_index]

            if 'hold' in settings:
                hold = settings.pop('hold')
            else:
                hold = True

            if 'reset' in settings:
                reset = settings.pop('reset')
            else:
                reset = False

            new_show = self.machine.light_controller.run_registered_script(
                script_name=self.active_profile_steps[self.current_step_index]['light_script'],
                lights=self.config['light'],
                leds=self.config['led'],
                priority=self.profiles[0][1],
                hold=hold,
                reset=reset,
                **self.active_profile_steps[self.current_step_index])

            if new_show:
                self.running_light_show = new_show
            else:
                self.log.warning("Error running light_script '%s'",
                    self.active_profile_steps[self.current_step_index]['light_script'])
                self.running_light_show = None

        else:
            self.running_light_show = None

    def _update_lights(self, step=0):

        if 'light_script' in self.active_profile_steps[self.current_step_index]:

            settings = self.active_profile_steps[self.current_step_index]

            if 'hold' in settings:
                hold = settings.pop('hold')
            else:
                hold = True

            if 'reset' in settings:
                reset = settings.pop('reset')
            else:
                reset = False

            self.running_light_show = (
                self.machine.light_controller.run_registered_script(
                    script_name=settings['light_script'],
                    lights=self.config['light'],
                    leds=self.config['led'],
                    start_location=step,
                    priority=self.active_profile_priority,
                    hold=hold,
                    reset=reset,
                    **settings))

    def _player_turn_start(self, player, **kwargs):
        """Called when a player's turn starts to update the player reference to
        the current player and to apply the default machine-wide shot profile.

        """
        self.player = player
        self.apply_profile(self.config['profile'], priority=0)

    def _player_turn_stop(self):
        self.player = None
        self.remove_profiles()

    def apply_profile(self, profile, priority, removal_key=None):
        """Applies a shot profile to this shot.

        Args:
            profile: String name of the profile to apply.
            priority: Priority of this profile. Only one profile is active at a
                time. If this profile is the highest, then it will be active. If
                not then it will still be applied and will become active if
                higher priority profiles are removed.
            removal_key: Optional hashable that can be used to identify this
                profile so it can be removed later.

        """
        if profile in self.machine.shot_controller.profiles:
            self.log.debug("Applying shot profile '%s', priority %s", profile,
                          priority)

            profile_tuple = (profile, priority,
                self.machine.shot_controller.profiles[profile],
                self.machine.shot_controller.profiles[profile]['steps'],
                removal_key)

            self.profiles.append(profile_tuple)

            self._sort_profiles()
            self._set_player_variable()
            self._update_current_step_variables()
            self._update_lights(step=-1)  # update with the the last step

        else:
            if not self.active_profile_name:
                self.apply_profile('default')

            self.log.debug("Shot profile '%s' not found. Shot is has '%s' "
                           "applied.", profile, self.active_profile_name)

    def remove_profile(self, removal_key=None, **kwargs):
        """Removes a shot profile from this shot.

        Args:
            removal_key: The key that was returned when the profile was applied
                to the shot which is how the profile you want to remove is
                identified. Default is None, in which case whichever profile is
                active will be removed.

        If the profile removed is the active one (because it was the highest
        priority), then this method activates the next-highest priority profile.

        Note that if there is only one profile applied, then it will not be
        removed.

        """

        if len(self.profiles) == 1:
            return

        if not removal_key:  # Get the key of the highest profile
            removal_key = self.profiles[0][4]

        old_profile = self.active_profile_name

        for entry in self.profiles[:]:  # slice so we can remove while iter
            if entry[4] == removal_key:
                self.profiles.remove(entry)

        self._sort_profiles()

        if self.active_profile_name != old_profile:

            self._stop_current_lights()
            self._set_player_variable()
            self._update_current_step_variables()
            self._update_lights()

    def remove_profiles(self, ):
        self._stop_current_lights()
        self.profiles = list()

    def _sort_profiles(self):
        self.profiles.sort(key=lambda x: x[1], reverse=True)

        (self.active_profile_name, self.active_profile_priority,
         self.active_profile_settings,
         self.active_profile_steps, _) = self.profiles[0]

    def hit(self, force=False, stealth=False, **kwargs):
        """Method which is called to indicate this shot was just hit. This
        method will advance the currently-active shot profile.

        Args:
            force: Boolean that forces this hit to be registered. Default is
                False which means if there are no balls in play (e.g. after a
                tilt) then this hit isn't processed. Set this to True if you
                want to force the hit to be processed even if no balls are in
                play.
            stealth: Boolean that controls whether this hit will post hit
                events. Useful if you want to just advance the step without
                triggering scoring, etc. Default is False.

        Note that the shot must be enabled in order for this hit to be
        processed.

        """

        if (not self.machine.game or (
                self.machine.game and not self.machine.game.balls_in_play) and
                not force):
            return

        if not self.enabled and not force:
            return

        if not stealth:

            self.log.debug("Hit! Profile: %s, Current Step: %s",
                          self.active_profile_name, self.current_step_name)

            # post event <name>_<profile>_<step>_hit
            self.machine.events.post(self.name + '_' +
                                     self.active_profile_name + '_' +
                                     self.current_step_name + '_hit')

            for group in self.shot_groups:
                group.hit(profile_name=self.active_profile_name,
                          profile_step_name=self.current_step_name)


            if Shot.monitor_enabled:
                for callback in self.machine.monitors['shots']:
                    callback(name=self.name)

        self._advance_step()

    def _sequence_hit(self, switch_name, state, ms):
        # does this current switch meet the next switch in the progress index?
        if switch_name == self.config['sequence_switches'][self.sequence_index]:

            # are we at the end?
            if self.sequence_index == len(self.config['switches']) - 1:
                self.hit()
            else:
                # does this shot specific a time limit?
                if self.config['time']:
                    # do we need to set a delay?
                    if not self.sequence_delay:
                        self.delay.reset(name='shot_timer',
                                         ms=self.config['time'],
                                         callback=self._reset_timer)
                        self.sequence_delay = True

                # advance the progress index
                self.sequence_index += 1

    def _reset_timer(self):
        self.log.debug("Resetting this sequence timer")
        self.sequence_index = 0
        self.sequence_delay = False

    def add_to_shot_group(self, group):
        self.shot_groups.add(group)

    def remove_from_shot_group(self, group):
        self.shot_groups.discard(group)

    def jump(self, step, update_group=True, current_show_step=0):
        """Jumps to a certain step in the active shot profile.

        Args:
            step: int of the step number you want to jump to. Note that steps
                are zero-based, so the first step is 0.
            update_group: Boolean which controls whether this jump event should
                also contact the shot group this shot belongs to to see if
                it should update this group's complete status. Default is True.
                False is used for things like shot rotation where a shot
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

        self._update_lights(current_show_step)

    def advance(self, **kwargs):
        """Advances the active shot profile one step forward.

        If this profile is at the last step and configured to roll over, it will
        roll over to the first step. If this profile is at the last step and not
        configured to roll over, this method has no effect.

        """
        self.hit(force=True, stealth=True)

    def enable(self, **kwargs):
        """Enables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """

        self.log.debug("Enabling...")
        self._register_switch_handlers()
        self.enabled = True

    def disable(self, **kwargs):
        """Disables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """
        self.log.debug("Disabling...")
        self._reset_timer()
        self._remove_switch_handlers()
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the active shot profile back to the first step (Step 0).
        This method is the same as calling jump(0).

        """
        self._reset_timer()
        self.jump(step=0)



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
            self.shots.append(self.member_collection[shot])

    def register_member_switches(self):
        for shot in self.config[self.device_str]:
            self.member_collection[shot].add_to_shot_group(self)

    def deregister_member_switches(self):
        for shot in self.config[self.device_str]:
            self.member_collection[shot].remove_from_shot_group(self)

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
        self.enabled = True

        self.register_member_switches()

        for shot in self.shots:
            shot.enable()

    def disable(self, **kwargs):
        """Disables this shot group. Also disables all the shots in this
        group.

        """

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
            shot.remove_profile()

    def advance(self, **kwargs):
        """Advances the current active profile from every shot in the group
        one step forward.

        """
        for shot in self.shots:
            shot.advance()

    def rotate(self, direction='right', steps=1, **kwargs):
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

        """

        if not self.enabled:
            return

        shot_state_list = deque()

        for shot in self.shots:

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
        for i in range(len(self.shots)):
            self.shots[i].jump(step=shot_state_list[i][0],
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
