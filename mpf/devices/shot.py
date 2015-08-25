""" Contains Shots device base class."""
# shot.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import operator
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
        self.current_state_index = 0
        self.current_state_name = None
        self.running_light_show = None
        self.player_variable = None
        self.active_sequences = list()
        """List of tuples: (id, current_position_index, next_switch)"""
        self.player = None
        self.active_delay_switches = set()
        self.enabled = False
        self.switch_handlers_active = False
        self.enable_table = list()
        self.current_mode = None  # highest priority mode controlling this shot
        self.current_priority = -1  # -1 is how we know we need to do a first time sort

        if not self.config['profile']:
            self.config['profile'] = 'default'

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

        if self.switch_handlers_active:
            return

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

        self.switch_handlers_active = True

    def _remove_switch_handlers(self):

        if not self.switch_handlers_active:
            return

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

        self.switch_handlers_active = False

    def advance(self, steps=1, **kwargs):
        """Advances the active shot profile one step forward.

        If this profile is at the last step and configured to roll over, it will
        roll over to the first step. If this profile is at the last step and not
        configured to roll over, this method has no effect.

        """
        if self.debug:
            self.log.debug("Advancing %s state(s)", steps)

        if (self.player[self.player_variable] + steps >=
                len(self.active_profile['states'])):

            if self.active_profile['loop']:
                if self.debug:
                    self.log.debug("Active profile '%s' is in its final state "
                                   "based a player variable %s=%s. Profile "
                                   "setting for loop is True, so resetting to "
                                   "the first state.",self.active_profile_name,
                                   self.player_variable,
                                   self.player[self.player_variable])

                self.player[self.player_variable] = 0

            else:
                if self.debug:
                    self.log.debug("Active profile '%s' is in its final state "
                                    "based a player variable %s=%s. Profile "
                                    "setting for loop is False, so state is not "
                                    "advancing.",self.active_profile_name,
                                    self.player_variable,
                                    self.player[self.player_variable])
                return
        else:

            if self.debug:
                self.log.debug("Advancing player variable %s %s state(s)",
                               self.player_variable, steps)

            self.machine.game.player[self.player_variable] += steps

        self._stop_current_lights()
        self._update_current_state_variables()
        self._update_lights()

    def _stop_current_lights(self):

        if self.debug:
            self.log.debug("Stopping current lights. Show: %s",
                           self.running_light_show)

        try:
            self.running_light_show.stop(hold=False, reset=False)
        except AttributeError:
            pass

        if self.debug:
            self.log.debug("Setting current light show to: None")

        self.running_light_show = None

    def _update_current_state_variables(self):
        self.current_state_index = self.player[self.player_variable]

        self.current_state_name = (
            self.active_profile['states'][self.current_state_index]['name'])

    def _update_lights(self, lightshow_step=0):

        #self._stop_current_lights()

        if self.debug:
            self.log.debug("Entering _update_lights(). Profile: %s, "
                           "lightshow_step: %s, Shot enabled: %s, Config "
                           "setting for 'lights_when_disabled': %s",
                           self.active_profile_name, lightshow_step,
                           self.enabled, self.active_profile['lights_when_disabled'])

        if not self.enabled and not self.active_profile['lights_when_disabled']:
            return

        state_settings = self.active_profile['states'][self.current_state_index]

        if self.debug:
            self.log.debug("Profile: '%s', State: %s, State settings: %s, "
                           "Lights: %s, LEDs: %s, Priority: %s",
                           self.active_profile_name, self.current_state_name,
                           state_settings, self.current_priority,
                           self.config['light'], self.config['led'])

        if state_settings['light_script'] and (self.config['light'] or
                                              self.config['led']):

            self.running_light_show = (
                self.machine.light_controller.run_registered_script(
                    script_name=state_settings['light_script'],
                    lights=[x.name for x in self.config['light']],
                    leds=[x.name for x in self.config['led']],
                    start_location=lightshow_step,
                    priority=self.current_priority,
                    **state_settings))

        if self.debug:
            self.log.debug("New running light show: %s",
                           self.running_light_show)

    def player_turn_start(self, player, **kwargs):
        """Called by the shot profile manager when a player's turn starts to
        update the player reference to the current player and to apply the
        default machine-wide shot profile.

        """
        self.player = player
        self.update_enable_table(self.config['profile'], False)

    def player_turn_stop(self):
        """Called by the shot profile manager when the player's turn ends.
        Removes the profiles from the shot and removes the player reference.

        """
        self.player = None
        self.remove_from_enable_table(None)
        self.current_priority = -1

        # if len(self.enable_table) > 1:
        #     print "enable table still has stuff even though player ended"
        #     print self.enable_table
        #     quit()

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

        self._remove_switch_handlers()
        self._stop_current_lights()

        del self.machine.shots[self.name]

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
            self.log.debug("Hit! Profile: %s, Current State: %s",
                          self.active_profile_name, self.current_state_name)

        # post events
        self.machine.events.post(self.name + '_hit',
                                 profile=self.active_profile_name,
                                 state=self.current_state_name)

        self.machine.events.post(self.name + '_' +
                                 self.active_profile_name + '_hit',
                                 profile=self.active_profile_name,
                                 state=self.current_state_name)

        self.machine.events.post(self.name + '_' +
                                 self.active_profile_name + '_' +
                                 self.current_state_name + '_hit',
                                 profile=self.active_profile_name,
                                 state=self.current_state_name)

        if Shot.monitor_enabled:
            for callback in self.machine.monitors['shots']:
                callback(name=self.name)

        if self.active_profile['advance_on_hit']:
            self.advance()
        elif self.debug:
            self.log.debug('Not advancing profile state since the current '
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

    def jump(self, state, lightshow_step=0):
        """Jumps to a certain state in the active shot profile.

        Args:
            state: int of the state number you want to jump to. Note that states
                are zero-based, so the first state is 0.
            lightshow_step: The step number that the associated light script
                should start playing at. Useful with rotations so this shot can
                pick up right where it left off. Default is 0.

        """
        if not self.machine.game:
            return

        if state == self.player[self.player_variable]:
            # we're already at that state
            return

        if self.debug:
            self.log.debug("Jumping to profile state '%s'", state)

        self._stop_current_lights()
        self.player[self.player_variable] = state
        self._update_current_state_variables()  # curr_state_index, curr_state_name

        self._update_lights(lightshow_step=lightshow_step)

    def enable(self, mode=None, profile=None, **kwargs):
        """

        """

        if self.debug:
            self.log.debug("Received command to enable this shot from mode: %s "
                           "with profile: %s", mode, profile)

        # if there's no profile, see if there's one in the table for this mode
        if not profile:
            try:
                profile = [x['profile'] for x in self.enable_table
                           if x['mode'] == mode][0]
            except IndexError:
                try:
                    profile = mode.config['shots'][self.name]['profile']
                except (KeyError, AttributeError):
                    profile = self.config['profile']

        self.update_enable_table(profile, True, mode)

    def _enable(self):

        if self.debug:
            self.log.debug("Enabling...")

        self.enabled = True

        self._register_switch_handlers()
        self.enabled = True

        # TODO should this see if this shot is configured to allow lights while
        # not enabled, and then not do this if they're already going?
        self._stop_current_lights()
        self._update_lights()

    def disable(self, mode=None, **kwargs):
        """Disables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """

        # we still want the profile here in case the shot is configured to have
        # lights even when disabled

        try:
            profile = mode.config['shots'][self.name]['profile']
        except (KeyError, AttributeError):
            profile = self.config['profile']

        self.update_enable_table(profile, False, mode)

    def _disable(self):

        if self.debug:
            self.log.debug("Disabling...")

        self._reset_all_sequences()
        self._remove_switch_handlers()
        self.delay.clear()
        self.enabled = False

        if not self.active_profile['lights_when_disabled']:
            self._stop_current_lights()

    def reset(self, **kwargs):
        """Resets the active shot profile back to the first state (State 0).
        This method is the same as calling jump(0).

        """
        if self.debug:
            self.log.debug("Resetting. Current profile '%s' will be reset to "
                           "its initial state", self.active_profile_name)

        self._reset_all_sequences()
        self.jump(state=0)

    def _sort_enable_table(self):

        if not self.enable_table:
            return

        if self.debug:
            old_highest = self.enable_table[0]

        # find the highest entry
        self.enable_table.sort(key=operator.itemgetter('priority'),
                               reverse=True)

        if self.debug:
            self.log.debug("Sorting the enable_table. New highest entry: %s, "
                           "Previous highest: %s",
                           self.enable_table[0], old_highest)

        self.current_mode = self.enable_table[0]['mode']

        if self.current_mode:
            self.current_priority = self.current_mode.priority
        else:
            self.current_priority = 0


        old_profile_name = self.active_profile_name

        self.active_profile_name = self.enable_table[0]['profile']

        if old_profile_name != self.active_profile_name:

            if self.debug:
                self.log.debug("New active profile: %s",
                               self.active_profile_name)

            try:
                self.active_profile = self.machine.shot_profile_manager.profiles[self.active_profile_name]
            except KeyError:
                self.log.error("Cannot apply profile '%s' because that is not a"
                               "valid profile name.", self.active_profile_name)
                sys.exit()

            self.active_profile_states = self.active_profile['states']

            # need to call
            self._stop_current_lights()
            self._set_player_variable()
            self._update_current_state_variables()
                # self.current_state_index
                # self.current_state_name

        # are we enabled when we weren't before?
        if self.enable_table[0]['enable'] and not self.enabled:
            self._enable()

        elif (self.enable_table[0]['enable'] and self.enabled and
                old_profile_name != self.active_profile_name):
            self._update_lights()  # can we not do this if it's the same profile?

        else:
            self._disable()

    def update_enable_table(self, profile, enable, mode=None):

        if mode:
            priority = mode.priority
        else:
            priority = 0

        lights_when_disabled = (self.machine.shot_profile_manager.profiles
                                [profile]['lights_when_disabled'])

        this_entry = {'mode': mode,
                      'priority': priority,
                      'profile': profile,
                      'enable': enable,
                      'lights_when_disabled': lights_when_disabled}

        if self.debug:
                self.log.debug("Updating the entry table: %s", this_entry)

        # Remove this mode's entry from the list if it's in there
        self.enable_table = [x for x in self.enable_table if x['mode'] != mode]

        self.enable_table.append(this_entry)
        self._sort_enable_table()

    def remove_from_enable_table(self, mode):
        self.enable_table = [x for x in self.enable_table if x['mode'] != mode]
        self._sort_enable_table()

    def remove_active_profile(self, mode, **kwargs):
        # this has the effect of changing out this mode's profile in the
        # enable_table with the next highest visable one.

        temp_list = [x for x in self.enable_table
                     if x['priority'] < mode.priority]

        for entry in temp_list:
            if entry['enable'] or (
                    not entry['enable'] and entry['lights_when_disabled']):

                profile = entry['profile']
                break

        enable = [x['enable'] for x in self.enable_table if x['mode']==mode][0]

        self.update_enable_table(profile, enable, mode)


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
