"""A shot in MPF."""

import uuid
from copy import copy

import mpf.core.delays
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


class Shot(ModeDevice, SystemWideDevice):

    """A device which represents a generic shot."""

    config_section = 'shots'
    collection = 'shots'
    class_label = 'shot'

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track shots.
    """

    def __init__(self, machine, name):
        """Initialise shot."""
        # If this device is setup in a machine-wide config, make sure it has
        # a default enable event.
        super(Shot, self).__init__(machine, name)

        self.delay = mpf.core.delays.DelayManager(self.machine.delayRegistry)

        self.active_sequences = list()
        """List of tuples: (id, current_position_index, next_switch)"""
        self.player = None
        self.active_delays = set()
        self.switch_handlers_active = False
        self.profiles = list()
        self.groups = set()  # shot_groups this shot belongs to

        # todo is this a hack??
        self.machine.events.add_handler('game_ended', self.disable)

        # todo remove this hack
        self._created_system_wide = False

    @property
    def enabled(self):
        """Return true if enabled."""
        return [x for x in self.profiles if x['enable']]

    @classmethod
    def prepare_config(cls, config, is_mode_config):
        """Add default events when not in mode."""
        if not is_mode_config:
            if 'enable_events' not in config:
                config['enable_events'] = 'ball_starting'
            if 'disable_events' not in config:
                config['disable_events'] = 'ball_ended'
            if 'reset_events' not in config:
                config['reset_events'] = 'ball_ended'
        return config

    def device_added_system_wide(self):
        """Called when a device is added system wide."""
        super().device_added_system_wide()
        self._created_system_wide = True

        self.update_profile(profile=self.config['profile'], enable=False,
                            mode=None)

    def device_added_to_mode(self, mode, player):
        """Called when this shot is dynamically added to a mode that was already started.

        Automatically enables the shot and calls the the method
        that's usually called when a player's turn starts since that was missed
        since the mode started after that.
        """
        super().device_added_to_mode(mode, player)

        self.player_turn_start(player)

        if not self.config['enable_events']:
            self.enable(mode)

    def _validate_config(self):
        if len(self.config['switch_sequence']) and (len(self.config['switch']) or len(self.config['switches']) or
                                                    len(self.config['sequence'])):
            raise AssertionError("Config error in shot {}. A shot can have "
                                 "either switch_sequence, sequence or "
                                 "switch/switches".format(self))

    def _initialize(self):
        self._validate_config()

        if not self.config['profile']:
            self.config['profile'] = 'default'

        if self.config['switch_sequence']:
            self.config['sequence'] = [self.machine.switch_controller.get_active_event_for_switch(x.name)
                                       for x in self.config['switch_sequence']]
            self.config['switch_sequence'] = []

        for switch in self.config['switch']:
            if switch not in self.config['switches']:
                self.config['switches'].append(switch)

    def _register_switch_handlers(self):
        if self.switch_handlers_active:
            return

        for switch in self.config['switches']:
            self.machine.switch_controller.add_switch_handler(
                switch.name, self.hit, 1)

        for event in self.config['sequence']:
            self.machine.events.add_handler(event, self._sequence_advance, event_name=event)

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

        self._reset_all_sequences()
        self.delay.clear()

        for switch in self.config['switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self.hit, 1)

        self.machine.events.remove_handler(self._sequence_advance)

        for switch in self.config['cancel_switch']:
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._cancel_switch_hit, 1)

        for switch in list(self.config['delay_switch'].keys()):
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._delay_switch_hit, 1)

        self.switch_handlers_active = False

    def advance(self, steps=1, mode=None, force=False, **kwargs):
        """Advance a shot profile forward.

        If this profile is at the last step and configured to loop, it will
        roll over to the first step. If this profile is at the last step and not
        configured to loop, this method has no effect.
        """
        del kwargs

        profile_settings = self.get_profile_by_key('mode', mode)

        if not (profile_settings['enable'] or force):
            return

        profile_name = profile_settings['profile']
        profile = profile_settings['settings']
        player_var = profile['player_variable']

        self.debug_log("Advancing %s step(s). Mode: %s, Profile: %s, "
                       "Current State: %s", steps, mode, profile_name,
                       self.player[player_var])

        if self.player[player_var] + steps >= len(profile['states']):

            if profile['loop']:
                self.player[profile['player_variable']] = 0

            else:
                return
        else:

            self.debug_log("Advancing player variable %s %s state(s)",
                           player_var, steps)

            self.player[player_var] += steps

        # update state
        self.update_current_state_name(mode)

        for group in self.groups:
            group.check_for_complete(mode)
            # TODO should be made to work for lower priority things too?

        self._update_show(mode=mode, show_step=self.player[player_var] + 1)

    def _stop_shows(self):
        for profile in self.profiles:
            self._stop_show(profile['mode'])

    def _stop_show(self, mode):
        profile = self.get_profile_by_key('mode', mode)

        if not profile or not profile['running_show']:
            return

        profile['running_show'].stop()
        profile['running_show'] = None

    def _update_shows(self, show_step=None, advance=None):
        for profile in self.profiles:
            self._update_show(mode=profile['mode'], show_step=show_step,
                              advance=advance)

    def _update_show(self, mode, show_step=None, advance=True):
        if not self.player:
            return

        profile = self.get_profile_by_key('mode', mode)

        try:
            if (not profile['enable'] and
                    not profile['settings']['show_when_disabled']):
                self._stop_show(profile['mode'])
                return

        except TypeError:
            return

        state_settings = (profile['settings']['states'][self.player[
                          profile['settings']['player_variable']]])

        if state_settings['show']:  # there's a show specified this state
            if profile['running_show']:
                if (profile['running_show'].show.name != state_settings['show'] or
                        profile['running_show'].current_step_index != state_settings['start_step'] or
                        profile['running_show'].manual_advance != state_settings['manual_advance']):
                    # if there's a show running and it's not the show for this
                    # state, stop it (and then continue)
                    self._stop_show(mode)
                else:
                    # if there's a show running and it is the one for this
                    # state, do nothing. Let it continue
                    return

            self._play_show(profile=profile, settings=state_settings)

        elif profile['settings']['show']:
            # no show for this state, but we have a profile root show
            if profile['running_show']:
                # is the running show the profile root one or a step-specific
                # one from the previous step?
                if (profile['running_show'].show.name !=
                        profile['settings']['show']):  # not ours
                    self._stop_show(profile['mode'])

                    # start the new show at this step
                    self._play_show(profile=profile, settings=state_settings, start_step=self.player[profile[
                        'settings']['player_variable']] + 1)

                elif advance:  # our show is the current one, just advance it
                    profile['running_show'].advance(show_step=show_step)

            else:  # no running show, so start the profile root show
                start_step = self.player[profile['settings']['player_variable']] + 1
                self._play_show(profile=profile, settings=state_settings, start_step=start_step)

        # if neither if/elif above happens, it means the current step has no
        # show but the previous step had one. That means we do nothing for the
        # show. Leave it alone doing whatever it was doing before.

    def _play_show(self, profile, settings, start_step=None):

        s = copy(settings)
        if settings['show']:
            show_name = settings['show']
            if s['manual_advance'] is None:
                s['manual_advance'] = False

        else:
            show_name = profile['settings']['show']
            if s['manual_advance'] is None:
                s['manual_advance'] = True

        s['show_tokens'] = self.config['show_tokens']
        s['priority'] += profile['priority']
        if start_step:
            s['start_step'] = start_step

        s.pop('show')
        s.pop('name')
        s.pop('action')

        profile['running_show'] = self.machine.shows[show_name].play(**s)

    def player_turn_start(self, player, **kwargs):
        """Update the player reference to the current player and to apply the default machine-wide shot profile.

        Called by the shot profile manager when a player's turn starts.
        """
        del kwargs
        self.player = player
        self._update_shows(advance=False)
        if self._created_system_wide:
            self.update_profile()

    def player_turn_stop(self):
        """Remove the profiles from the shot and remove the player reference.

        Called by the shot profile manager when the player's turn ends.
        """
        self.player = None
        self.remove_profile_by_mode(None)

    def add_control_events_in_mode(self, mode):
        """Add control events in mode."""
        enable = not mode.config['shots'][self.name]['enable_events']
        self.update_profile(enable=enable, mode=mode)

    def device_removed_from_mode(self, mode):
        """Remove this shot device.

        Destroys it and removes it from the shots collection.
        """
        del mode
        if self._created_system_wide:
            return

        self.debug_log("Removing...")
        self.disable()
        self._remove_switch_handlers()
        self._stop_shows()

    def _build_waterfall_list(self, mode):
        _wf = list()
        found = False

        for _profile in self.profiles:
            if _profile['mode'] == mode:
                found = True
            elif found:
                _wf.append(_profile['mode'])
                if self.get_profile_by_key('mode', _profile['mode'])['settings']['block']:
                    break
        return _wf

    def hit(self, mode='default#$%', _wf=None, **kwargs):
        """Advance the currently-active shot profile.

        Args:
            mode: (Optional) The mode instance that was hit. If this is not
                specified, this hit is registered via the highest-priority mode
                that this shot is active it. A value of None represents the
                base machine config (e.g. no Mode). The crazy default string
                it so this method can differentiate between no mode specified
                (where it uses the highest one) and a value of "None" which is
                the base machine-wide config.
            _wf: (Internal use only) A list of remaining modes from the enable
                table of the original hit. Used to waterfall hits (which is
                where hits are cascaded down to this shot in lower priority
                modes if blocking is not set.

        Note that the shot must be enabled in order for this hit to be
        processed.
        """
        del kwargs

        # Stop if there is an active delay but no sequence
        if (self.active_delays and
                not len(self.config['sequence'])):
            return

        if mode == 'default#$%':
            mode = self.get_profile_by_key('enable', True)['mode']

        try:
            if not self.get_profile_by_key('enable', True)['enable']:
                return
        except TypeError:
            return

        profile_settings = self.get_profile_by_key('mode', mode)

        if not profile_settings:
            return

        profile = profile_settings['profile']
        state = profile_settings['current_state_name']

        self.debug_log("Hit! Mode: %s, Profile: %s, State: %s",
                       mode, profile, state)

        # do this before the events are posted since events could change the
        # profile
        if not _wf and not self.get_profile_by_key(
                'mode', mode)['settings']['block']:
            _wf = self._build_waterfall_list(mode)
        elif _wf:
            _wf.pop(0)

        # post events
        if not _wf:
            # if this is a waterfall, this event would have already been posted
            self.machine.events.post('{}_hit'.format(self.name),
                                     profile=profile, state=state)
            '''event: (shot)_hit
            desc: The shot called (shot) was just hit.

            Note that there are three events posted when a shot is hit, each
            with variants of the shot name, profile, and current state,
            allowing you to key in on the specific granularity you need.

            args:
            profile: The name of the profile that was active when hit.
            state: The name of the state the profile was in when it was hit'''

        self.machine.events.post('{}_{}_hit'.format(self.name, profile),
                                 profile=profile, state=state)
        '''event: (shot)_(profile)_hit
        desc: The shot called (shot) was just hit with the profile (profile)
        active.

        Note that there are three events posted when a shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''

        self.machine.events.post('{}_{}_{}_hit'.format(self.name, profile,
                                                       state),
                                 profile=profile, state=state)
        '''event: (shot)_(profile)_(state)_hit
        desc: The shot called (shot) was just hit with the profile (profile)
        active in the state (state).

        Note that there are three events posted when a shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) and (state) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''

        # Need to try because the event postings above could be used to stop
        # the mode, in which case the mode entry won't be in the profiles list
        try:
            advance = self.get_profile_by_key('mode', mode)['settings']['advance_on_hit']
        except KeyError:
            advance = False

        if advance:
            self.debug_log("Mode '%s' advance_on_hit is True.", mode)
            self.advance(mode=mode)
        else:
            self.debug_log('Not advancing profile state since the current '
                           'mode %s has setting advance_on_hit set to '
                           'False or this mode is not in the profiles list',
                           mode)

        for group in [x for x in self.groups]:
            self.log.debug("Notifying shot_group %s of new hit", group)
            group.hit(mode, profile, state)

        self._notify_monitors(profile, state)

        # if not the last in the waterfall propagate
        if _wf:
            self.hit(_wf[0], _wf)

        else:
            self.debug_log('%s settings has block enabled', mode)

    def _notify_monitors(self, profile, state):
        if Shot.monitor_enabled and "shots" in self.machine.monitors:
            for callback in self.machine.monitors['shots']:
                callback(name=self.name, profile=profile, state=state)

    def _sequence_advance(self, event_name, **kwargs):
        # Since we can track multiple simulatenous sequences (e.g. two balls
        # going into an orbit in a row), we first have to see whether this
        # switch is starting a new sequence or continuing an existing one
        del kwargs

        self.debug_log("Sequence advance: %s", event_name)

        if event_name == self.config['sequence'][0]:
            if len(self.config['sequence']) > 1:
                # if there is more than one step
                self._start_new_sequence()
            else:
                # only one step means we complete instantly
                self.hit()

        else:
            # Get the seq_id of the first sequence this switch is next for.
            # This is not a loop because we only want to advance 1 sequence
            seq_id = next((x[0] for x in self.active_sequences if
                           x[2] == event_name), None)

            if seq_id:
                # advance this sequence
                self._advance_sequence(seq_id)

    def _start_new_sequence(self):
        # If the sequence hasn't started, make sure we're not within the
        # delay_switch hit window

        if self.active_delays:
            self.debug_log("There's a delay switch timer in effect from "
                           "switch(es) %s. Sequence will not be started.",
                           self.active_delays)
            return

        # create a new sequence
        seq_id = uuid.uuid4()
        next_event = self.config['sequence'][1]

        self.debug_log("Setting up a new sequence. Next: %s", next_event)

        self.active_sequences.append((seq_id, 0, next_event))

        # if this sequence has a time limit, set that up
        if self.config['time']:
            self.debug_log("Setting up a sequence timer for %sms",
                           self.config['time'])

            self.delay.reset(name=seq_id,
                             ms=self.config['time'],
                             callback=self._reset_sequence,
                             seq_id=seq_id)

    def _advance_sequence(self, seq_id):
        # get this sequence
        seq_id, current_position_index, next_event = next(
            x for x in self.active_sequences if x[0] == seq_id)

        # Remove this sequence from the list
        self.active_sequences.remove((seq_id, current_position_index,
                                      next_event))

        if current_position_index == (len(self.config['sequence']) - 2):  # complete

            self.debug_log("Sequence complete!")

            self.delay.remove(seq_id)
            self.hit()

        else:
            current_position_index += 1
            next_event = self.config['sequence'][current_position_index + 1]

            self.debug_log("Advancing the sequence. Next: %s",
                           next_event)

            self.active_sequences.append(
                (seq_id, current_position_index, next_event))

    def _cancel_switch_hit(self):
        self._reset_all_sequences()

    def _delay_switch_hit(self, switch_name, state, ms):
        del state
        del ms
        self.delay.reset(name=switch_name + '_delay_timer',
                         ms=self.config['delay_switch']
                                       [self.machine.switches[switch_name]],
                         callback=self._release_delay,
                         switch=switch_name)

        self.active_delays.add(switch_name)

    def _release_delay(self, switch):
        self.active_delays.remove(switch)

    def _reset_sequence(self, seq_id):
        self.debug_log("Resetting this sequence")

        self.active_sequences = [x for x in self.active_sequences
                                 if x[0] != seq_id]

    def _reset_all_sequences(self):
        seq_ids = [x[0] for x in self.active_sequences]

        for seq_id in seq_ids:
            self.delay.remove(seq_id)

        self.active_sequences = list()

    def jump(self, mode, state, show_step=1, force=True):
        """Jump to a certain state in the active shot profile.

        Args:
            state: int of the state number you want to jump to. Note that states
                are zero-based, so the first state is 0.
            show_step: The step number that the associated light script
                should start playing at. Useful with rotations so this shot can
                pick up right where it left off. Default is 1 (the first step
                in the show)

        """
        if not (self.get_profile_by_key('mode', mode)['enable'] or force):
            return

        try:
            if state == self.player[self.get_profile_by_key('mode', mode)['settings']['player_variable']]:
                # we're already at that state
                return
        except KeyError:  # no profile for this mode
            return

        self.debug_log("Jumping to profile state '%s'", state)

        self.player[
            self.get_profile_by_key('mode', mode)['settings']['player_variable']] = state
        self.update_current_state_name(mode)

        self.debug_log("Jump is for active mode. Updating lights")

        self._update_show(mode=mode, show_step=show_step)

    def enable(self, mode=None, profile=None, **kwargs):
        """Enable shot."""
        del kwargs

        self.debug_log("Received command to enable this shot from mode: %s "
                       "with profile: %s", mode, profile)

        self.update_profile(profile=profile, enable=True, mode=mode)

    def disable(self, mode=None, **kwargs):
        """Disable this shot.

        If the shot is not enabled, hits to it will not be processed.
        """
        del kwargs
        self.update_profile(enable=False, mode=mode)

    def reset(self, mode=None, **kwargs):
        """Reset the shot profile for the passed mode back to the first state (State 0) and reset all sequences."""
        del kwargs
        self.debug_log("Resetting. Mode profile '%s' will be reset to "
                       "its initial state", mode)

        self._reset_all_sequences()
        self.jump(mode, state=0)

    def update_current_state_name(self, mode):
        """Update current state name."""
        profile = self.get_profile_by_key('mode', mode)

        try:

            profile['current_state_name'] = (
                profile['settings']['states'][self.player[profile['settings'][
                    'player_variable']]]['name'])

        except TypeError:
            profile['current_state_name'] = None

    def remove_active_profile(self, mode='default#$%', **kwargs):
        """Remove the active profile."""
        del kwargs
        # this has the effect of changing out this mode's profile in the
        # profiles list with the next highest visible one.

        if mode == 'default#$%':
            mode = self.get_profile_by_key('enable', True)['mode']

        self.update_profile(enable=False, mode=mode)

        # self.get_profile_by_key('mode', mode)['enable'] = False

        self.debug_log("Removing active profile for mode %s", mode)

        # todo

    def update_profile(self, profile=None, enable=None, mode=None):
        """Update profile."""
        existing_profile = self.get_profile_by_key('mode', mode)

        if not existing_profile:  # we're adding, not updating
            self._add_profile2(profile=profile, enable=enable, mode=mode)
            return

        update_needed = False

        if profile and profile != existing_profile['profile']:
            update_needed = True
            try:
                existing_profile['settings'] = (
                    self.machine.shot_profile_manager.profiles[profile].copy())
                existing_profile['settings']['player_variable'] = (
                    existing_profile['settings']['player_variable'].replace(
                        '%', self.name))
                existing_profile['profile'] = profile

            except KeyError:
                raise AssertionError('Cannot apply shot profile "{}" to shot "{}" as'
                                     ' there is no profile with that name.'.format(profile, self.name))

        if isinstance(enable, bool) and enable != existing_profile['enable']:
            update_needed = True
            existing_profile['enable'] = enable

        if update_needed:
            self._process_changed_profiles()
            self._update_show(mode=mode, advance=False)
            self.update_current_state_name(mode)  # todo

    def add_profile(self, profile_dict):
        """Add a profile to shot."""
        self.profiles.append(profile_dict)
        self._update_show(mode=profile_dict['mode'], advance=False)
        self._sort_profiles()

    def _add_profile2(self, profile=None, enable=None, mode=None):
        if mode:
            priority = mode.priority
        else:
            priority = 0

        if not profile:
            try:
                profile = self.get_profile_by_key('mode', mode)['profile']
            except TypeError:
                profile = self.config['profile']

        if enable is None:
            enable = False

        try:
            profile_settings = (
                self.machine.shot_profile_manager.profiles[profile].copy())
        except KeyError:
            raise AssertionError('Cannot apply shot profile "{}" to shot "{}" as '
                                 'there is no profile with that name.'.format(profile, self.name))

        profile_settings['player_variable'] = (
            profile_settings['player_variable'].replace('%', self.name))

        this_entry = dict(current_state_name=None,
                          running_show=None,
                          mode=mode)

        this_entry['priority'] = priority
        this_entry['profile'] = profile
        this_entry['settings'] = profile_settings
        this_entry['enable'] = enable

        self.add_profile(this_entry)

        self.update_current_state_name(mode)  # todo

    def remove_profile_by_mode(self, mode):
        """Remove profile for mode."""
        self._stop_show(mode)  # todo
        self.profiles[:] = [x for x in self.profiles if x['mode'] != mode]
        self._process_changed_profiles()

    def get_profile_by_key(self, key, value):
        """Return profile for a key value pair."""
        try:
            return [x for x in self.profiles if x[key] == value][0]
        except IndexError:
            return None

    def _sort_profiles(self):
        self.profiles = sorted(self.profiles, key=lambda x: x['priority'],
                               reverse=True)

        self._process_changed_profiles()

    def _process_changed_profiles(self):
        # todo bug? profile[0] disabled should still allow lower ones to work?

        if self.get_profile_by_key('enable', True):
            self._register_switch_handlers()
        else:
            self._remove_switch_handlers()

    def register_group(self, group):
        """Register a group.

        Notify this shot that it has been added to a group, meaning it
        will update this group of its state changes. Note this is called by
        :class:``ShotGroup``. If you want to manually add a shot to a group,
        do it from there.
        """
        self.debug_log("Received request to register this shot to the %s "
                       "group", group)

        self.groups.add(group)

    def deregister_group(self, group):
        """Deregister a group.

        Notify this shot that it is no longer part of this group. Note
        this is called by :class:``ShotGroup``. If you want to manually
        remove a shot from a group, do it from there.
        """
        self.debug_log("Received request to deregister this shot from the %s "
                       "group", group)

        self.groups.discard(group)
