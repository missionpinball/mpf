""" Contains Shots device base class."""
# shot.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import uuid

from mpf.system.device import Device
from mpf.system.config import Config
from mpf.system.timing import Timing
from mpf.system.tasks import DelayManager


class Shot(Device):

    config_section = 'shots'
    collection = 'shots'
    class_label = 'shot'

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track shots.
    """

    def __init__(self, machine, name, config, collection=None):
        super(Shot, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        self.active_profile_name = None
        self.active_profile = dict()
        self.active_profile_priority = 0
        self.current_step_index = 0
        self.current_step_name = None
        self.running_light_show = None
        self.shot_groups = set()
        self.profiles = list()
        """List of tuples:
        (profile_name, priority, profile_config, steps, key)
        """

        self.player_variable = None

        self.active_sequences = list()
        """List of tuples:
        (id, current_position_index, next_switch)
        """

        self.player = None
        self.active_delay_switches = set()

        self.enabled = False

        if self.debug:
            self._enable_related_device_debugging()

    def _enable_related_device_debugging(self):

        self.log.debug("Enabling debugging for this shot's leds and lights")

        for led in self.config['led']:
            led.enable_debugging()

        for light in self.config['light']:
            light.enable_debugging()

    def _disable_related_device_debugging(self):
        for led in self.config['led']:
            led.disable_debugging()

        for light in self.config['light']:
            light.disable_debugging()

    def _set_player_variable(self):
        if self.active_profile['player_variable']:
            self.player_variable = self.active_profile['player_variable']
        else:
            self.player_variable = (self.name + '_' + self.active_profile_name)

    def _register_switch_handlers(self):
        for switch in self.config['switch']:
            self.machine.switch_controller.add_switch_handler(
                switch.name, self.hit, 1)

        for switch in self.config['switch_sequence']:
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._sequence_switch_hit, 1, return_info=True)

        for switch in self.config['cancel_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._cancel_switch_hit, 1)

        for switch in self.config['delay_switch'].keys():
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._delay_switch_hit, 1, return_info=True)

    def _remove_switch_handlers(self):
        for switch in self.config['switch']:
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self.hit, 1)

        for switch in self.config['switch_sequence']:
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._sequence_switch_hit, 1)

        for switch in self.config['cancel_switch']:
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._cancel_switch_hit, 1)

        for switch in self.config['delay_switch'].keys():
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._delay_switch_hit, 1)

    def advance(self, steps=1, **kwargs):
        """Advances the active shot profile one step forward.

        If this profile is at the last step and configured to roll over, it will
        roll over to the first step. If this profile is at the last step and not
        configured to roll over, this method has no effect.

        """
        if self.debug:
            self.log.debug("Advancing %s step(s)", steps)

        if (self.player[self.player_variable] + steps >=
                len(self.active_profile['steps'])):

            if self.active_profile['loop']:
                if self.debug:
                    self.log.debug("Active profile 's' is in its final step "
                                   "based a player variable %s=%s. Profile "
                                   "setting for loop is True, so resetting to "
                                   "the first step.",self.active_profile_name,
                                   self.player_variable,
                                   self.player[self.player_variable])

                self.player[self.player_variable] = 0

            else:
                if self.debug:
                    self.log.debug("Active profile 's' is in its final step "
                                    "based a player variable %s=%s. Profile "
                                    "setting for loop is False, so step is not "
                                    "advancing.",self.active_profile_name,
                                    self.player_variable,
                                    self.player[self.player_variable])
                return
        else:

            if self.debug:
                self.log.debug("Advancing player variable %s %s step(s)",
                               self.player_variable, steps)

            self.machine.game.player[self.player_variable] += steps

        self._stop_current_lights()
        self._update_current_step_variables()
        self._update_lights()
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
            self.active_profile['steps'][self.current_step_index]['name'])

    def _update_lights(self, lightshow_step=0):

        if self.debug:
            self.log.debug("Entering _update_lights(). lightshow_step: %s, Shot"
                           " enabled: %s, Config setting for "
                           "'lights_when_disabled': %s", lightshow_step,
                           self.enabled, self.config['lights_when_disabled'])

        if not self.enabled and not self.config['lights_when_disabled']:
            return

        step_settings = self.active_profile['steps'][self.current_step_index]

        if self.debug:
            self.log.debug("Current profile step settings: %s", step_settings)

        if step_settings['light_script'] and (self.config['light'] or
                                              self.config['led']):

            self.running_light_show = (
                self.machine.light_controller.run_registered_script(
                    script_name=step_settings['light_script'],
                    lights=[x.name for x in self.config['light']],
                    leds=[x.name for x in self.config['led']],
                    start_location=lightshow_step,
                    priority=self.active_profile_priority,
                    **step_settings))

    def player_turn_start(self, player, **kwargs):
        """Called when a player's turn starts to update the player reference to
        the current player and to apply the default machine-wide shot profile.

        """
        self.player = player
        self.apply_profile(self.config['profile'], priority=0)

    def player_turn_stop(self):
        """Called when the player's turn ends. Removes the profiles from the
        shot and removes the player reference.

        """
        self.player = None
        self.remove_profiles()

    def device_added_to_mode(self, player):
        """Called when this shot is dynamically added to a mode that was
        already started. Automatically enables the shot and calls the the method
        that's usually called when a player's turn starts since that was missed
        since the mode started after that.

        """
        self.player_turn_start(player)

        if not self.config['enable_events']:
            self.enable()

    def remove(self):
        """Remove this shot device. Destroys it and removes it from the shots
        collection.

        """

        if self.debug:
            self.log.debug("Removing...")

        for group in self.shot_groups:

            try:
                group.remove_member_shot(self)
            except ValueError:
                pass

        self._remove_switch_handlers()
        self._stop_current_lights()

        del self.machine.shots[self.name]

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
        if profile in self.machine.shot_profile_manager.profiles:
            if self.debug:
                self.log.debug("Applying shot profile '%s', priority %s",
                               profile, priority)

            profile_tuple = (profile, priority,
                self.machine.shot_profile_manager.profiles[profile],
                self.machine.shot_profile_manager.profiles[profile]['steps'],
                removal_key)

            if profile_tuple not in self.profiles:
                self.profiles.append(profile_tuple)

            self._sort_profiles()
            self._set_player_variable()
            self._update_current_step_variables()
            self._update_lights()

        else:
            if not self.active_profile:
                self.apply_profile('default', priority)

            if self.debug:
                self.log.debug("Shot profile '%s' not found. Shot is has '%s' "
                               "applied.", profile, self.active_profile_name)

    def remove_active_profile(self):
        """Removes the current active shot profile and restores whichever one is
        the next-highest. Note that if there is only one active profile, then
        this method has no effect (since shots are required to have at least one
        active profile.)

        """
        if len(self.profiles) > 1:
            removal_key = self.profiles[0][4]
            self.remove_profile_by_key(removal_key)

    def remove_profile_by_name(self, profile_name, **kwargs):
        """Removes an active profile by name.

        Args:
            profile_name: String name of the profile to remove.

        Note that if the profile_name is the only active profile for this shot,
        then it will not be removed since each shot needs to have at least one
        active profile.

        """
        for profile in self.profiles:
            if profile[0] == profile_name:
                self.remove_profile_by_key(profile[4])
                return

    def remove_profile_by_key(self, removal_key, **kwargs):
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

    def remove_profiles(self):
        """Removes all the profiles for this shot and reapplies the default
        profile specified in the machine-wide config.

        """
        if len(self.profiles) > 1:

            self._stop_current_lights()
            self.profiles = list()
            self.apply_profile(self.config['profile'], 0)

    def _sort_profiles(self):
        self.profiles.sort(key=lambda x: x[1], reverse=True)

        (self.active_profile_name,
         self.active_profile_priority,
         self.active_profile,
         self.active_profile['steps'], _) = self.profiles[0]

    def hit(self, force=False, **kwargs):
        """Method which is called to indicate this shot was just hit. This
        method will advance the currently-active shot profile.

        Args:
            force: Boolean that forces this hit to be registered. Default is
                False which means if there are no balls in play (e.g. after a
                tilt) then this hit isn't processed. Set this to True if you
                want to force the hit to be processed even if no balls are in
                play.

        Note that the shot must be enabled in order for this hit to be
        processed.

        """
        # Why 3 ifs here? Less brain hurting trying to follow the logic. :)
        if (not self.machine.game or (
                self.machine.game and not self.machine.game.balls_in_play) and
                not force):
            return

        if not self.enabled and not force:
            return

        if self.active_delay_switches and not force:
            return

        if self.debug:
            self.log.debug("Hit! Profile: %s, Current Step: %s",
                          self.active_profile_name, self.current_step_name)

        # post events
        self.machine.events.post(self.name + '_hit',
                                 profile=self.active_profile_name,
                                 step=self.current_step_name)

        self.machine.events.post(self.name + '_' +
                                 self.active_profile_name + '_hit',
                                 profile=self.active_profile_name,
                                 step=self.current_step_name)

        self.machine.events.post(self.name + '_' +
                                 self.active_profile_name + '_' +
                                 self.current_step_name + '_hit',
                                 profile=self.active_profile_name,
                                 step=self.current_step_name)

        for group in self.shot_groups:
            group.hit(profile_name=self.active_profile_name,
                      profile_step_name=self.current_step_name)

        if Shot.monitor_enabled:
            for callback in self.machine.monitors['shots']:
                callback(name=self.name)

        if self.active_profile['advance_on_hit']:
            self.advance()
        elif self.debug:
            self.log.debug('Not advancing profile step since the current '
                           'profile ("%s") has setting advance_on_hit set to '
                           'False', self.active_profile_name)

    def _sequence_switch_hit(self, switch_name, state, ms):
        # Since we can track multiple simulatenous sequences (e.g. two balls
        # going into an orbit in a row), we first have to see whether this
        # switch is starting a new sequence or continuing an existing one

        if self.debug:
            self.log.debug("Sequence switch hit: %s", switch_name)

        if switch_name == self.config['switch_sequence'][0].name:

            self._start_new_sequence()


        else:
            # Get the seq_id of the first sequence this switch is next for.
            # This is not a loop because we only want to advance 1 sequence
            seq_id = next((x[0] for x in self.active_sequences if
                           x[2]==switch_name), None)

            if seq_id:
                # advance this sequence
                self._advance_sequence(seq_id)

    def _start_new_sequence(self):
        # If the sequence hasn't started, make sure we're not within the
        # delay_switch hit window

        if self.active_delay_switches:
            if self.debug:
                self.log.debug("There's a delay switch timer in effect from "
                              "switch(es) %s. Sequence will not be started.",
                              self.active_delay_switches)
            return

        # create a new sequence
        seq_id = uuid.uuid4()
        next_switch = self.config['switch_sequence'][1].name

        if self.debug:
                self.log.debug("Setting up a new sequence. Next switch: %s",
                              next_switch)

        self.active_sequences.append(
            (seq_id, 0, next_switch)
            )

        # if this sequence has a time limit, set that up
        if self.config['time']:
            if self.debug:
                self.log.debug("Setting up a sequence timer for %sms",
                              self.config['time'])

            self.delay.reset(name='seq_id',
                             ms=self.config['time'],
                             callback=self._reset_sequence,
                             seq_id=seq_id)

    def _advance_sequence(self, seq_id):
        # get this sequence
        seq_id, current_position_index, next_switch = next(
            x for x in self.active_sequences if x[0]==seq_id)

        # Remove this sequence from the list
        self.active_sequences.remove((seq_id, current_position_index,
                                      next_switch))

        if current_position_index == (
            len(self.config['switch_sequence']) - 2):  # complete

            if self.debug:
                self.log.debug("Sequence complete!")

            self.delay.remove(seq_id)
            self.hit()

        else:
            current_position_index += 1
            next_switch = (self.config['switch_sequence']
                           [current_position_index+1].name)

            if self.debug:
                self.log.debug("Advancing the sequence. Next switch: %s",
                              next_switch)

            self.active_sequences.append(
                (seq_id, current_position_index, next_switch))

    def _cancel_switch_hit(self):
        self._reset_all_sequences()

    def _delay_switch_hit(self, switch_name, state, ms):
        self.delay.reset(name=switch_name + 'delay_timer',
                         ms=self.config['delay_switch'][switch_name],
                         callback=self._release_delay,
                         switch=switch_name)

        self.active_delay_switches.add(switch_name)

    def _release_delay(self, switch):
        self.active_delay_switches.remove(switch_name)

    def _reset_sequence(self, seq_id):
        if self.debug:
            self.log.debug("Resetting this sequence")

        sequence = [x for x in self.active_sequences if x[0]==seq_id]

        try:
            self.active_sequences.remove(sequence)
        except ValueError:
            pass

    def _reset_all_sequences(self):
        seq_ids = [x[0] for x in self.active_sequences]

        for seq_id in seq_ids:
            self.delay.remove(seq_id)

        self.active_sequences = list()

    def add_to_shot_group(self, group):
        """Adds this shot to a shot group.

        Args:
            group: String name of the shot_group this shot should be added to.

        Note that if this shot is already a member of that group, it is not
        added again.

        """
        if self.debug:
            self.log.debug('Adding this shot to group: %s', group.name)
        self.shot_groups.add(group)

    def remove_from_shot_group(self, group):
        """Removes this shot from a shot group.

        Args:
            group: String name of the shot_group this shot should be removed
                from.

        """
        if self.debug:
            self.log.debug('Removing this shot from group: %s', group.name)
        self.shot_groups.discard(group)

    def jump(self, step, update_group=True, lightshow_step=0):
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
            lightshow_step: The step number that the associated light script
                should start playing at. Useful with rotations so this shot can
                pick up right where it left off. Default is 0.

        """
        if not self.machine.game:
            return

        self._stop_current_lights()
        self.player[self.player_variable] = step
        self._update_current_step_variables()  # curr_step_index, curr_step_name

        if update_group:
            self._update_group_status()

        self._update_lights(lightshow_step=lightshow_step)

    def enable(self, **kwargs):
        """Enables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """

        if self.enabled:
            return

        if self.debug:
            self.log.debug("Enabling...")
        self._register_switch_handlers()
        self.enabled = True

        self._update_lights()

    def disable(self, **kwargs):
        """Disables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """

        if not self.enabled:
            return

        if self.debug:
            self.log.debug("Disabling...")
        self._reset_all_sequences()
        self._remove_switch_handlers()
        self.delay.clear()
        self.enabled = False

        if not self.config['lights_when_disabled']:
            self._stop_current_lights()

    def reset(self, **kwargs):
        """Resets the active shot profile back to the first step (Step 0).
        This method is the same as calling jump(0).

        """
        self._reset_all_sequences()
        self.jump(step=0)


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
