""" Contains Shots device base class."""

import uuid
from collections import OrderedDict

from mpf.core.device import Device
import mpf.core.tasks


class Shot(Device):
    config_section = 'shots'
    collection = 'shots'
    class_label = 'shot'

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track shots.
    """

    def __init__(self, machine, name, config, collection=None, validate=True):
        # If this device is setup in a machine-wide config, make sure it has
        # a default enable event.

        # TODO add a mode parameter to the device constructor and do the logic
        # there.
        if not machine.modes:

            if 'enable_events' not in config:
                config['enable_events'] = 'ball_starting'
            if 'disable_events' not in config:
                config['disable_events'] = 'ball_ended'
            if 'reset_events' not in config:
                config['reset_events'] = 'ball_ended'

        super(Shot, self).__init__(machine, name, config, collection,
                                   validate=validate)

        self.delay = mpf.core.tasks.DelayManager(self.machine.delayRegistry)

        self.running_light_show = None
        self.active_sequences = list()
        """List of tuples: (id, current_position_index, next_switch)"""
        self.player = None
        self.active_delay_switches = set()
        self.switch_handlers_active = False
        self.enable_table = OrderedDict()
        self.groups = set()  # shot_groups this shot belongs to

        self.active_mode = None
        self.active_settings = None

        if not self.config['profile']:
            self.config['profile'] = 'default'

        if not self.machine.modes:
            self.update_enable_table(profile=self.config['profile'],
                                     enable=False,
                                     mode=None)

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

        for switch in list(self.config['delay_switch'].keys()):
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

        for switch in list(self.config['delay_switch'].keys()):
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._delay_switch_hit, 1)

        self.switch_handlers_active = False

    def advance(self, steps=1, mode=None, **kwargs):
        """Advances a shot profile forward.

        If this profile is at the last step and configured to roll over, it will
        roll over to the first step. If this profile is at the last step and not
        configured to roll over, this method has no effect.

        """

        profile_name = self.enable_table[mode]['profile']
        profile = self.enable_table[mode]['settings']
        player_var = profile['player_variable']

        if self.debug:
            self.log.debug("Advancing %s step(s). Mode: %s, Profile: %s, "
                           "Current State: %s", steps, mode, profile_name,
                           self.player[player_var])

        if self.player[player_var] + steps >= len(profile['states']):

            if profile['loop']:
                if self.debug:
                    self.log.debug("Profile '%s' is in its final state "
                                   "based a player variable %s=%s. Profile "
                                   "setting for loop is True, so resetting to "
                                   "the first state.",
                                   self.active_settings['profile'],
                                   player_var, self.player[player_var])

                self.player[profile['player_variable']] = 0

            else:
                if self.debug:
                    self.log.debug("Profile '%s' is in its final state "
                                   "based a player variable %s=%s. Profile "
                                   "setting for loop is False, so state is not "
                                   "advancing.",
                                   self.active_settings['profile'],
                                   player_var, self.player[player_var])
                return
        else:

            if self.debug:
                self.log.debug("Advancing player variable %s %s state(s)",
                               player_var, steps)

            self.player[player_var] += steps
            self.update_current_state_name(mode)

            for group in self.groups:
                group.check_for_complete(mode)
                # TODO should be made to work for lower priority things too?

        if self.active_settings['profile'] == profile_name:

            if self.debug:
                self.log.debug("Profile '%s' just advanced is the active "
                               "profile", profile_name)

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

    def _update_lights(self, lightshow_step=0):
        self._stop_current_lights()

        if not self.player:
            return

        if self.debug:
            self.log.debug("Updating lights 1: Profile: %s, "
                           "lightshow_step: %s, Enabled: %s, Config "
                           "setting for 'lights_when_disabled': %s",
                           self.active_settings['profile'], lightshow_step,
                           self.active_settings['enable'],
                           self.active_settings['settings'][
                               'lights_when_disabled'])

        if (not self.active_settings['enable'] and
                not self.active_settings['settings']['lights_when_disabled']):
            return

        state_settings = (self.active_settings['settings']['states']
                          [self.player[
                self.active_settings['settings']['player_variable']]])

        if self.debug:
            self.log.debug(
                "Updating lights 2: Profile: '%s', State: %s, State "
                "settings: %s, Lights: %s, LEDs: %s, Priority: %s",
                self.active_settings['profile'],
                self.enable_table[self.active_mode]['current_state_name'],
                state_settings, self.config['light'],
                self.config['led'], self.active_settings['priority'])

        if state_settings['light_script'] and (self.config['light'] or
                                                   self.config['led']):
            self.running_light_show = (
                self.machine.show_controller.run_registered_light_script(
                    script_name=state_settings['light_script'],
                    lights=[x.name for x in self.config['light']],
                    leds=[x.name for x in self.config['led']],
                    start_location=lightshow_step,
                    priority=self.active_settings['priority'],
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
        # self.update_enable_table(self.config['profile'], False)

    def player_turn_stop(self):
        """Called by the shot profile manager when the player's turn ends.
        Removes the profiles from the shot and removes the player reference.

        """
        self.player = None
        self.remove_from_enable_table(None)
        self.active_settings['priority'] = -1

    def device_added_to_mode(self, mode, player):
        """Called when this shot is dynamically added to a mode that was
        already started. Automatically enables the shot and calls the the method
        that's usually called when a player's turn starts since that was missed
        since the mode started after that.

        """
        self.player_turn_start(player)

        # if not self.config['enable_events']:
        #     self.enable(mode)

    def control_events_in_mode(self, mode):

        if self.debug:
            self.log.debug('Control events found in %s config. Updating'
                           ' enable_table', mode)

        if not mode.config['shots'][self.name]['enable_events']:
            enable = True
        else:
            enable = False

        self.update_enable_table(enable=enable,
                                 mode=mode)

    def remove(self):
        """Remove this shot device. Destroys it and removes it from the shots
        collection.

        """

        if self.debug:
            self.log.debug("Removing...")

        self._remove_switch_handlers()
        self._stop_current_lights()

        del self.machine.shots[self.name]

    def hit(self, mode='default#$%', waterfall_hits=None,
            **kwargs):
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
        if (not self.machine.game or
                (self.machine.game and not self.machine.game.balls_in_play) or
                self.active_delay_switches):
            return

        if mode == 'default#$%':
            mode = self.active_mode

        profile, state = self.get_mode_state(mode)

        if self.debug:
            self.log.debug("Hit! Mode: %s, Profile: %s, State: %s",
                           mode, profile, state)

        # do this before the events are posted since events could change the
        # profile
        if not self.enable_table[mode]['settings']['block']:
            need_to_waterfall = True
        else:
            need_to_waterfall = False

        # post events
        self.machine.events.post(self.name + '_hit', profile=profile,
                                 state=state)
        self.machine.events.post(self.name + '_' + profile + '_hit',
                                 profile=profile, state=state)
        self.machine.events.post(self.name + '_' + profile + '_' + state +
                                 '_hit', profile=profile, state=state)

        # Need to try because the event postings above could be used to stop
        # the mode, in which case the mode entry won't be in the enable_table
        try:
            advance = self.enable_table[mode]['settings']['advance_on_hit']
        except KeyError:
            advance = False

        if advance:
            if self.debug:
                self.log.debug("Mode '%s' advance_on_hit is True.", mode)
            self.advance(mode=mode)
        elif self.debug:
            self.log.debug('Not advancing profile state since the current '
                           'mode %s has setting advance_on_hit set to '
                           'False or this mode is not in the enable_table',
                           mode)

        for group in [x for x in self.groups]:
            self.log.debug("Notifying shot_group %s of new hit", group)
            group.hit(mode, profile, state)

        if Shot.monitor_enabled:
            for callback in self.machine.monitors['shots']:
                callback(name=self.name, profile=profile, state=state)

        if need_to_waterfall:

            if self.debug:
                self.log.debug('%s block: False. Waterfalling hits', mode)

            if not waterfall_hits:
                waterfall_hits = set()

            self._waterfall_hits(mode, waterfall_hits.add(profile))

        elif self.debug:
            self.log.debug('%s settings has block enabled', mode)

    def _waterfall_hits(self, mode, waterfall_hits):

        # check for waterfall_hits here because the current active profile
        # could have been changed and we know for sure we want to look for
        # waterfall_hits regardless of what it is since we're here.
        if waterfall_hits and mode.enable_table[mode]['settings']['block']:
            return

        found = False

        for _mode, settings in self.enable_table.items():
            # only care about hits lower than this mode

            if found:
                self.hit(mode=_mode, waterfall_hits=waterfall_hits)
                return

            elif _mode != mode:
                continue

            elif _mode == mode:
                found = True

    def get_mode_state(self, mode):
        # returns a tuple of profile_name, current_state_name

        # if the mode is not in the enable_table, that means this shot is not
        # used in that mode, so we return False

        if self.debug:
            self.log.debug("Checking state of enable_table for %s", mode)

        if mode in self.enable_table:
            return (self.enable_table[mode]['profile'],
                    self.enable_table[mode]['current_state_name'])
        else:
            return False

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
                           x[2] == switch_name), None)

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

            self.delay.reset(name=seq_id,
                             ms=self.config['time'],
                             callback=self._reset_sequence,
                             seq_id=seq_id)

    def _advance_sequence(self, seq_id):
        # get this sequence
        seq_id, current_position_index, next_switch = next(
            x for x in self.active_sequences if x[0] == seq_id)

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
                           [current_position_index + 1].name)

            if self.debug:
                self.log.debug("Advancing the sequence. Next switch: %s",
                               next_switch)

            self.active_sequences.append(
                (seq_id, current_position_index, next_switch))

    def _cancel_switch_hit(self):
        self._reset_all_sequences()

    def _delay_switch_hit(self, switch_name, state, ms):
        self.delay.reset(name=switch_name + '_delay_timer',
                         ms=self.config['delay_switch']
                                       [self.machine.switches[switch_name]],
                         callback=self._release_delay,
                         switch=switch_name)

        self.active_delay_switches.add(switch_name)

    def _release_delay(self, switch):
        self.active_delay_switches.remove(switch)

    def _reset_sequence(self, seq_id):
        if self.debug:
            self.log.debug("Resetting this sequence")

        self.active_sequences = [x for x in self.active_sequences
                                 if x[0] != seq_id]

    def _reset_all_sequences(self):
        seq_ids = [x[0] for x in self.active_sequences]

        for seq_id in seq_ids:
            self.delay.remove(seq_id)

        self.active_sequences = list()

    def jump(self, mode, state, lightshow_step=0):
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

        if self.debug:
            self.log.debug(
                'Jump. Mode: %s, New state #: %s, Current state #: %s, Player var:'
                '%s, Lightshow_step: %s', mode, state,
                self.player[
                    self.enable_table[mode]['settings']['player_variable']],
                self.enable_table[mode]['settings']['player_variable'],
                lightshow_step)

        if state == self.player[
            self.enable_table[mode]['settings']['player_variable']]:
            # we're already at that state
            return

        if self.debug:
            self.log.debug("Jumping to profile state '%s'", state)

        self.player[
            self.enable_table[mode]['settings']['player_variable']] = state
        self.update_current_state_name(mode)

        if mode == self.active_mode:

            if self.debug:
                self.log.debug("Jump is for active mode. Updating lights")

            self._update_lights(lightshow_step=lightshow_step)

        elif self.debug:
            self.log.debug("Jump mode: %s, Active mode: %s. Not updating "
                           "lights", mode, self.active_mode)

    def enable(self, mode=None, profile=None, **kwargs):
        """

        """

        if self.debug:
            self.log.debug(
                "Received command to enable this shot from mode: %s "
                "with profile: %s", mode, profile)

        self.update_enable_table(profile=profile, enable=True, mode=mode)

    def _enable(self):

        if self.debug:
            self.log.debug("Enabling...")

        self._register_switch_handlers()

        # TODO should this see if this shot is configured to allow lights while
        # not enabled, and then not do this if they're already going?
        self._update_lights()

    def disable(self, mode=None, **kwargs):
        """Disables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """

        # we still want the profile here in case the shot is configured to have
        # lights even when disabled

        self.update_enable_table(enable=False, mode=mode)

    def _disable(self):

        if self.debug:
            self.log.debug("Disabling...")

        self._reset_all_sequences()
        self._remove_switch_handlers()
        self.delay.clear()

        if not self.active_settings['settings']['lights_when_disabled']:
            self._stop_current_lights()

    def reset(self, mode=None, **kwargs):
        """Resets the shot profile for the passed mode back to the first state (State 0).
        This method is the same as calling jump(0).

        """
        if self.debug:
            self.log.debug("Resetting. Mode profile '%s' will be reset to "
                           "its initial state", mode)

        self._reset_all_sequences()
        self.jump(mode, state=0)

    def _sort_enable_table(self):

        if self.debug:
            self.log.debug("Sorting enable_table")

        old_mode = self.active_mode
        old_settings = self.active_settings

        self.enable_table = OrderedDict(sorted(list(self.enable_table.items()),
                                               key=lambda x: x[1]['priority'],
                                               reverse=True))

        # set a pointer to the highest entry
        for mode, settings in self.enable_table.items():
            self.active_mode = mode
            self.active_settings = settings

            break

        if self.debug:
            self.log.debug("New enable_table order: %s",
                           list(self.enable_table.keys()))

        # top profile has changed
        if (not old_settings or
                    old_settings['profile'] != self.active_settings[
                    'profile']):

            if self.debug:
                self.log.debug("New top entry settings: %s",
                               self.active_settings)

        # are we enabled?
        if self.active_settings['enable']:
            self._enable()

        else:
            self._disable()

    def update_enable_table(self, profile=None, enable=None, mode=None):

        if mode:
            priority = mode.priority
        else:
            priority = 0

        if not profile:
            try:
                profile = self.enable_table[mode]['profile']
            except KeyError:
                profile = self.config['profile']

        if not enable:
            try:
                enable = self.enable_table[mode]['enable']
            except KeyError:
                enable = False

        profile_settings = (
            self.machine.shot_profile_manager.profiles[profile].copy())

        profile_settings['player_variable'] = (
            profile_settings['player_variable'].replace('%', self.name))

        this_entry = {'priority': priority,
                      'profile': profile,
                      'enable': enable,
                      'settings': profile_settings,
                      'current_state_name': None
                      }

        if self.debug:
            self.log.debug("Updating the entry table with: %s:%s", mode,
                           this_entry)

        self.enable_table[mode] = this_entry
        self.update_current_state_name(mode)
        self._sort_enable_table()

    def remove_from_enable_table(self, mode):

        if self.debug:
            self.log.debug("Removing mode: %s from enable_table", mode)

        try:
            del self.enable_table[mode]
            self._sort_enable_table()
        except KeyError:
            pass

    def update_current_state_name(self, mode):

        if self.debug:
            self.log.debug("Old current state name for mode %s: %s",
                           mode, self.enable_table[mode]['current_state_name'])

        try:
            self.enable_table[mode]['current_state_name'] = (
                self.enable_table[mode]['settings']['states']
                [self.player[self.enable_table[mode]['settings']
                ['player_variable']]]['name'])
        except TypeError:
            self.enable_table[mode]['current_state_name'] = None

        if self.debug:
            self.log.debug("New current state name for mode %s: %s",
                           mode, self.enable_table[mode]['current_state_name'])

    def remove_active_profile(self, mode, **kwargs):
        # this has the effect of changing out this mode's profile in the
        # enable_table with the next highest visable one.

        if self.debug:
            self.log.debug("Removing active profile for mode %s", mode)

        for k, v in self.enable_table.items():
            if (v['priority'] < self.enable_table[mode]['priority'] and
                    (v['enable'] or v['settings']['lights_when_disabled'])):

                if self.debug:
                    self.log.debug("Applying active profile from mode %s", k)

                self.update_enable_table(profile=v['profile'],
                                         enable=v['enable'],
                                         mode=mode)

                return

    def add_to_group(self, group):

        if self.debug:
            self.log.debug("Received request to add this shot to the %s group",
                           group)

        if type(group) is str:

            try:
                group = self.machine.shot_groups[group]
            except KeyError:
                if self.debug:
                    self.log.debug("'%s' is not a valid shot_group name.",
                                   group)
                return

        self.groups.add(group)

    def remove_from_group(self, group):

        if self.debug:
            self.log.debug("Received request to remove this shot from the %s "
                           "group", group)

        if type(group) is str:

            try:
                group = self.machine.shot_groups[group]
            except KeyError:
                if self.debug:
                    self.log.debug("'%s' is not a valid shot_group name.",
                                   group)
                return

        self.groups.discard(group)

    def _update_groups(self, profile, state):
        for group in self.groups:
            group.update_member_shot(shot=self, profile=profile, state=state)
