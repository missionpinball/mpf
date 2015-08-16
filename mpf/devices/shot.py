""" Contains the base classes for Shots."""
# shot.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import uuid

from mpf.system.devices import Device
from mpf.system.config import Config
from mpf.system.timing import Timing
from mpf.system.tasks import DelayManager


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

        self.sequence_index = 0
        self.sequence_delay = False
        self.player = None
        self.active_delay_switches = set()

        self.enabled = False

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

    def _advance_step(self, steps=1):
        if (self.player[self.player_variable] + 1 >=
                len(self.active_profile['steps'])):
            if self.active_profile['loop']:
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
            self.active_profile['steps'][self.current_step_index]['name'])

    def _do_step_actions(self, ):
        if ('light_script' in self.active_profile['steps'][self.current_step_index]
                and (self.config['light'] or self.config['led'])):

            settings = self.active_profile['steps'][self.current_step_index]

            if 'hold' in settings:
                hold = settings.pop('hold')
            else:
                hold = True

            if 'reset' in settings:
                reset = settings.pop('reset')
            else:
                reset = False

            new_show = self.machine.light_controller.run_registered_script(
                script_name=self.active_profile['steps'][self.current_step_index]['light_script'],
                lights=[x.name for x in self.config['light']],
                leds=[x.name for x in self.config['led']],
                priority=self.profiles[0][1],
                hold=hold,
                reset=reset,
                **self.active_profile['steps'][self.current_step_index])

            if new_show:
                self.running_light_show = new_show
            else:
                self.log.warning("Error running light_script '%s'",
                    self.active_profile['steps'][self.current_step_index]['light_script'])
                self.running_light_show = None

        else:
            self.running_light_show = None

    def _update_lights(self, step=0):
        if 'light_script' in self.active_profile['steps'][self.current_step_index]:

            settings = self.active_profile['steps'][self.current_step_index]

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
                    lights=[x.name for x in self.config['light']],
                    leds=[x.name for x in self.config['led']],
                    start_location=step,
                    priority=self.active_profile_priority,
                    hold=hold,
                    reset=reset,
                    **settings))

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
        if profile in self.machine.shot_controller.profiles:
            if self.debug:
                self.log.debug("Applying shot profile '%s', priority %s",
                               profile, priority)

            profile_tuple = (profile, priority,
                self.machine.shot_controller.profiles[profile],
                self.machine.shot_controller.profiles[profile]['steps'],
                removal_key)

            if profile_tuple not in self.profiles:
                self.profiles.append(profile_tuple)

            self._sort_profiles()
            self._set_player_variable()
            self._update_current_step_variables()
            self._update_lights(step=-1)  # update with the the last step

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
        # Why 3 ifs here? Less brain hurting trying to follow the logic. :)
        if (not self.machine.game or (
                self.machine.game and not self.machine.game.balls_in_play) and
                not force):
            return

        if not self.enabled and not force:
            return

        if self.active_delay_switches and not force:
            return

        if not stealth:

            if self.debug:
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

    def _sequence_switch_hit(self, switch_name, state, ms):
        # Since we can track multiple simulatenous sequences (e.g. two balls
        # going into an orbit in a row), we first have to see whether this
        # switch is starting a new sequence or continuing an existing one

        if self.debug:
            self.log.info("Sequence switch hit: %s", switch_name)

        if switch_name == self.config['switch_sequence'][0].name:
            self._start_new_sequence()

        else:
            # loop through all the sequences
            for sequence in self.active_sequences:

                # if we find one with the next step at this switch, advance it
                if sequence[2] == switch_name:
                    self._advance_sequence(sequence[0])

                    # stop looping. Only want to advance one sequence per hit.
                    return


    def _start_new_sequence(self):
        # If the sequence hasn't started, make sure we're not within the
        # delay_switch hit window



        if self.active_delay_switches:

            if self.debug:
                self.log.info("There's a delay switch timer in effect from "
                              "switch(es) %s. Sequence will not be started.",
                              self.active_delay_switches)

            return

        # create a new sequence
        seq_id = uuid.uuid4()
        next_switch = self.config['switch_sequence'][1].name

        if self.debug:
                self.log.info("Setting up a new sequence. Next switch: %s",
                              next_switch)

        self.active_sequences.append(
            (seq_id, 0, next_switch)
            )

        # if this sequence has a delay, set that up
        if self.config['time']:
            if self.debug:
                self.log.info("Setting up a sequence timer for %sms",
                              self.config['time'])

            self.delay.reset(name='seq_id',
                             ms=self.config['time'],
                             callback=self._reset_sequence,
                             seq_id=seq_id)
            self.sequence_delay = True

    def _advance_sequence(self, seq_id):
        # get this sequence
        for sequence in self.active_sequences:
            if sequence[0] == seq_id:
                seq_id, current_position_index, next_switch = sequence

                # Remove this sequence from the set
                self.active_sequences.remove(sequence)

                if current_position_index == (
                    len(self.config['switch_sequence']) - 2):  # complete

                    if self.debug:
                        self.log.info("Sequence complete!")

                    # TODO remove the delay
                    self.hit()

                else:
                    current_position_index += 1
                    next_switch = (self.config['switch_sequence']
                                   [current_position_index].name)

                    if self.debug:
                        self.log.info("Advancing the sequence. Next switch: %s",
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

        for sequence in self.active_sequences[:]:
            if sequence[0] == seq_id:
                seq_id, current_position_index, next_switch = sequence

                # Remove this sequence from the set
                self.active_sequences.remove(sequence)

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

        if self.enabled:
            return

        if self.debug:
            self.log.debug("Enabling...")
        self._register_switch_handlers()
        self.enabled = True

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
