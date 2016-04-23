"""
Shot
====

A shot in MPF is a cool thing.

"""

import uuid
from collections import OrderedDict
from copy import copy

import mpf.core.delays
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.config_validator import ConfigValidator


class Shot(ModeDevice, SystemWideDevice):
    config_section = 'shots'
    collection = 'shots'
    class_label = 'shot'

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track shots.
    """

    def __init__(self, machine, name):
        # If this device is setup in a machine-wide config, make sure it has
        # a default enable event.
        super(Shot, self).__init__(machine, name)

        self.delay = mpf.core.delays.DelayManager(self.machine.delayRegistry)

        self.running_show = None
        self.active_sequences = list()
        """List of tuples: (id, current_position_index, next_switch)"""
        self.player = None
        self.active_delay_switches = set()
        self.switch_handlers_active = False
        self.enable_table = OrderedDict()
        self.groups = set()  # shot_groups this shot belongs to

        self.active_mode = None
        self.active_settings = None
        self._enabled = False
        self.tokens = dict()

        # todo is this a hack??
        self.machine.events.add_handler('game_ended', self.disable)

    @property
    def enabled(self):
        return self._enabled

    def prepare_config(self, config, is_mode_config):
        if not is_mode_config:
            if 'enable_events' not in config:
                config['enable_events'] = 'ball_starting'
            if 'disable_events' not in config:
                config['disable_events'] = 'ball_ended'
            if 'reset_events' not in config:
                config['reset_events'] = 'ball_ended'
        return config

    def device_added_system_wide(self):
        # Called when a device is added system wide
        super().device_added_system_wide()

        self.update_enable_table(profile=self.config['profile'],
                                 enable=False,
                                 mode=None)

    def device_added_to_mode(self, mode, player):
        """Called when this shot is dynamically added to a mode that was
        already started. Automatically enables the shot and calls the the method
        that's usually called when a player's turn starts since that was missed
        since the mode started after that.

        """
        super().device_added_to_mode(mode, player)

        self.player_turn_start(player)

        if not self.config['enable_events']:
            self.enable(mode)

    def _validate_config(self):
        if len(self.config['switch_sequence']) and (
                    len(self.config['switch']) or len(self.config['switches'])):
            raise AssertionError("A shot can have either switch_sequence or "
                                 "switch/switches, not both")

    def _initialize(self):
        self._validate_config()

        if not self.config['profile']:
            self.config['profile'] = 'default'

        for switch in self.config['switch']:
            if switch not in self.config['switches']:
                self.config['switches'].append(switch)

        self._create_tokens()

    def _create_tokens(self):
        # anything in this shot's config that is not a standard shot config
        # item is a token that's later passed to shows
        self.tokens = {x: self.config[x] for x in self.config
                       if x not in ConfigValidator.config_spec['shots']}

    def _register_switch_handlers(self):
        if self.switch_handlers_active:
            return

        for switch in self.config['switches']:
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

        for switch in self.config['switches']:
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

    def advance(self, steps=1, mode=None, force=False, **kwargs):
        """Advances a shot profile forward.

        If this profile is at the last step and configured to loop, it will
        roll over to the first step. If this profile is at the last step and not
        configured to loop, this method has no effect.

        """
        del kwargs

        if not (self._enabled or force):
            return

        profile_name = self.enable_table[mode]['profile']
        profile = self.enable_table[mode]['settings']
        player_var = profile['player_variable']

        self.debug_log("Advancing %s step(s). Mode: %s, Profile: %s, "
                       "Current State: %s", steps, mode, profile_name,
                       self.player[player_var])

        if self.player[player_var] + steps >= len(profile['states']):

            if profile['loop']:
                self.debug_log("Profile '%s' is in its final state "
                               "based a player variable %s=%s. Profile "
                               "setting for loop is True, so resetting to "
                               "the first state.",
                               self.active_settings['profile'],
                               player_var, self.player[player_var])

                self.player[profile['player_variable']] = 0

            else:
                self.debug_log("Profile '%s' is in its final state "
                               "based a player variable %s=%s. Profile "
                               "setting for loop=0, so state is not "
                               "advancing.",
                               self.active_settings['profile'],
                               player_var, self.player[player_var])
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

        if self.active_settings['profile'] == profile_name:

            self.debug_log("Profile '%s' just advanced is the active "
                           "profile", profile_name)

            self._update_show()

    def _stop_show(self):
        if not self.running_show:
            return

        self.debug_log("Stopping current show: %s", self.running_show)

        self.running_show.stop(hold=False)

        self.debug_log("Setting current show to: None")

        self.running_show = None

    def _update_show(self, show_step=None, advance=True):
        if not self.player:
            return

        try:
            if (not self.active_settings['enable'] and
                    not self.active_settings['settings']['show_when_disabled']):
                return
        except TypeError:  # catches no active_settings
            return

        state_settings = (self.active_settings['settings']['states'][self.player[
                          self.active_settings['settings']['player_variable']]])

        if state_settings['show']:  # there's a show specified this state

            if self.running_show:
                if (self.running_show.show.name != state_settings['show']):
                    # if there's a show running and it's not the show for this
                    # state, stop it (and then continue)
                    self._stop_show()
                else:
                    # if there's a show running and it is the one for this
                    # state, do nothing. Let it continue
                    return

            # If we're here then we need to start the show from this state
            s = copy(state_settings)
            s.update(self.tokens)
            s.pop('show')

            self.running_show = (
                self.machine.shows[state_settings['show']].play(
                    mode=self.active_mode, **s))

        elif self.active_settings['settings']['show']:
            # no show for this state, but we have a profile root show
            if self.running_show:
                # is the running show the profile root one or a step-specific
                # one from the previous step?
                if (self.running_show.show.name !=
                        self.active_settings['settings']['show']):  # not ours
                    self._stop_show()

                    # start the new show at this step
                    s = copy(state_settings)
                    s.update(self.tokens)
                    s['manual_advance'] = True
                    s['start_step'] = self.player[self.active_settings[
                        'settings']['player_variable']] + 1
                    # +1 above because show steps are 1-based while player var
                    # profile index is 0-based
                    s.pop('show')
                    self.running_show = (self.machine.shows[
                        self.active_settings['settings']['show']].play(
                        mode=self.active_mode, **s))

                elif advance:  # our show is the current one, just advance it
                    self.running_show.advance(show_step=show_step)

            else:  # no running show, so start the profile root show
                s = copy(state_settings)
                s.update(self.tokens)
                s.pop('show')
                s['manual_advance'] = True

                self.running_show = (self.machine.shows[
                    self.active_settings['settings']['show']].play(
                    mode=self.active_mode, **s))

        # if neither if/elif above happens, it means the current step has no
        # show but the previous step had one. That means we do nothing for the
        # show. Leave it alone doing whatever it was doing before.

    def player_turn_start(self, player, **kwargs):
        """Called by the shot profile manager when a player's turn starts to
        update the player reference to the current player and to apply the
        default machine-wide shot profile.

        """
        del kwargs
        self.player = player
        self._update_show(advance=False)

    def player_turn_stop(self):
        """Called by the shot profile manager when the player's turn ends.
        Removes the profiles from the shot and removes the player reference.

        """
        self.player = None
        self.remove_from_enable_table(None)
        self.active_settings['priority'] = -1

    def control_events_in_mode(self, mode):

        self.debug_log('Control events found in %s config. Updating '
                       'enable_table', mode)

        enable = not mode.config['shots'][self.name]['enable_events']

        self.update_enable_table(enable=enable, mode=mode)

    def remove(self):
        """Remove this shot device. Destroys it and removes it from the shots
        collection.

        """

        self.debug_log("Removing...")
        self.disable()
        self._remove_switch_handlers()
        self._stop_show()

        del self.machine.shots[self.name]

    def hit(self, mode='default#$%', _wf=None, **kwargs):
        """Method which is called to indicate this shot was just hit. This
        method will advance the currently-active shot profile.

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

        if not self._enabled:
            return

        # Stop if there is an active delay but no sequence
        if (self.active_delay_switches and
                not len(self.config['switch_sequence'])):
            return

        if mode == 'default#$%':
            mode = self.active_mode

        profile, state = self.get_mode_state(mode)

        self.debug_log("Hit! Mode: %s, Profile: %s, State: %s",
                       mode, profile, state)

        # do this before the events are posted since events could change the
        # profile
        if not _wf and not self.enable_table[mode]['settings']['block']:
            _wf = list()
            found = False

            for _mode in self.enable_table:
                if _mode == mode:
                    found = True
                elif found:
                    _wf.append(_mode)
                    if self.enable_table[_mode]['settings']['block']:
                        break
        elif _wf:
            _wf.pop(0)

        # post events
        self.machine.events.post('{}_hit'.format(self.name),
                                 profile=profile, state=state)

        self.machine.events.post('{}_{}_hit'.format(self.name, profile),
                                 profile=profile, state=state)

        self.machine.events.post('{}_{}_{}_hit'.format(self.name, profile, state),
                                 profile=profile,
                                 state=state)

        # Need to try because the event postings above could be used to stop
        # the mode, in which case the mode entry won't be in the enable_table
        try:
            advance = self.enable_table[mode]['settings']['advance_on_hit']
        except KeyError:
            advance = False

        if advance:
            self.debug_log("Mode '%s' advance_on_hit is True.", mode)
            self.advance(mode=mode)
        else:
            self.debug_log('Not advancing profile state since the current '
                           'mode %s has setting advance_on_hit set to '
                           'False or this mode is not in the enable_table',
                           mode)

        for group in [x for x in self.groups]:
            self.log.debug("Notifying shot_group %s of new hit", group)
            group.hit(mode, profile, state)

        if Shot.monitor_enabled and "shots" in self.machine.monitors:
            for callback in self.machine.monitors['shots']:
                callback(name=self.name, profile=profile, state=state)

        if _wf:
            self.hit(_wf[0], _wf)

        else:
            self.debug_log('%s settings has block enabled', mode)

    def get_mode_state(self, mode):
        # returns a tuple of profile_name, current_state_name

        # if the mode is not in the enable_table, that means this shot is not
        # used in that mode, so we return False

        self.debug_log("Checking state of enable_table for %s", mode)

        if mode in self.enable_table:
            return (self.enable_table[mode]['profile'],
                    self.enable_table[mode]['current_state_name'])
        else:
            return False

    def _sequence_switch_hit(self, switch_name, state, ms):
        # Since we can track multiple simulatenous sequences (e.g. two balls
        # going into an orbit in a row), we first have to see whether this
        # switch is starting a new sequence or continuing an existing one
        del state
        del ms

        self.debug_log("Sequence switch hit: %s", switch_name)

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
            self.debug_log("There's a delay switch timer in effect from "
                           "switch(es) %s. Sequence will not be started.",
                           self.active_delay_switches)
            return

        # create a new sequence
        seq_id = uuid.uuid4()
        next_switch = self.config['switch_sequence'][1].name

        self.debug_log("Setting up a new sequence. Next switch: %s", next_switch)

        self.active_sequences.append((seq_id, 0, next_switch))

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
        seq_id, current_position_index, next_switch = next(
            x for x in self.active_sequences if x[0] == seq_id)

        # Remove this sequence from the list
        self.active_sequences.remove((seq_id, current_position_index,
                                      next_switch))

        if current_position_index == (
                    len(self.config['switch_sequence']) - 2):  # complete

            self.debug_log("Sequence complete!")

            self.delay.remove(seq_id)
            self.hit()

        else:
            current_position_index += 1
            next_switch = (self.config['switch_sequence']
                           [current_position_index + 1].name)

            self.debug_log("Advancing the sequence. Next switch: %s",
                           next_switch)

            self.active_sequences.append(
                (seq_id, current_position_index, next_switch))

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

        self.active_delay_switches.add(switch_name)

    def _release_delay(self, switch):
        self.active_delay_switches.remove(switch)

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
        """Jumps to a certain state in the active shot profile.

        Args:
            state: int of the state number you want to jump to. Note that states
                are zero-based, so the first state is 0.
            show_step: The step number that the associated light script
                should start playing at. Useful with rotations so this shot can
                pick up right where it left off. Default is 1 (the first step
                in the show)

        """
        if not (self._enabled or force):
            return

        self.debug_log(
                'Jump. Mode: %s, New state #: %s, Current state #: %s, Player var:'
                '%s, Lightshow_step: %s', mode, state,
                self.player[
                    self.enable_table[mode]['settings']['player_variable']],
                self.enable_table[mode]['settings']['player_variable'],
                show_step)

        if state == self.player[self.enable_table[mode]['settings'][
                                                        'player_variable']]:
            # we're already at that state
            return

        self.debug_log("Jumping to profile state '%s'", state)

        self.player[
            self.enable_table[mode]['settings']['player_variable']] = state
        self.update_current_state_name(mode)

        if mode == self.active_mode:

            self.debug_log("Jump is for active mode. Updating lights")

            self._update_show(show_step=show_step)

        else:
            self.debug_log("Jump mode: %s, Active mode: %s. Not updating "
                           "lights", mode, self.active_mode)

    def enable(self, mode=None, profile=None, **kwargs):
        del kwargs

        if self._enabled:
            return

        self.debug_log(
                "Received command to enable this shot from mode: %s "
                "with profile: %s", mode, profile)

        self.update_enable_table(profile=profile, enable=True, mode=mode)

    def _enable(self):

        self.debug_log("Enabling...")

        self._enabled = True

        self._register_switch_handlers()

        # TODO should this see if this shot is configured to allow lights while
        # not enabled, and then not do this if they're already going?
        self._update_show(advance=False)

    def disable(self, mode=None, **kwargs):
        """Disables this shot. If the shot is not enabled, hits to it will
        not be processed.

        """
        del kwargs
        if not self._enabled:
            return

        # we still want the profile here in case the shot is configured to have
        # lights even when disabled

        self.update_enable_table(enable=False, mode=mode)

    def _disable(self):
        self.debug_log("Disabling...")
        self._enabled = False
        self._reset_all_sequences()
        self._remove_switch_handlers()
        self.delay.clear()

        if not self.active_settings['settings']['show_when_disabled']:
            self._stop_show()
        else:
            self._update_show(advance=False)

    def reset(self, mode=None, **kwargs):
        """Resets the shot profile for the passed mode back to the first state (State 0) and
        resets all sequences.

        """
        del kwargs
        self.debug_log("Resetting. Mode profile '%s' will be reset to "
                       "its initial state", mode)

        self._reset_all_sequences()
        self.jump(mode, state=0)

    def _sort_enable_table(self):
        self.debug_log("Sorting enable_table")

        old_settings = self.active_settings

        self.enable_table = OrderedDict(sorted(list(self.enable_table.items()),
                                               key=lambda x: x[1]['priority'],
                                               reverse=True))

        # set a pointer to the highest entry
        for mode, settings in self.enable_table.items():
            self.active_mode = mode
            self.active_settings = settings
            break

        self.debug_log("New enable_table order: %s",
                       list(self.enable_table.keys()))

        # top profile has changed
        if not old_settings or old_settings['profile'] != self.active_settings['profile']:
            self.debug_log("New top entry settings: %s",
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

        if enable is None:
            try:
                enable = self.enable_table[mode]['enable']
            except KeyError:
                enable = False

        try:
            profile_settings = (
                self.machine.shot_profile_manager.profiles[profile].copy())
        except KeyError:
            raise KeyError('Cannot apply shot profile "{}" to shot "{}" as '
                           'there is no profile with that name.'.format(
                           profile, self.name))

        profile_settings['player_variable'] = (
            profile_settings['player_variable'].replace('%', self.name))

        this_entry = {'priority': priority,
                      'profile': profile,
                      'enable': enable,
                      'settings': profile_settings,
                      'current_state_name': None
                      }

        self.debug_log("Updating the entry table with: %s:%s", mode,
                       this_entry)

        self.enable_table[mode] = this_entry
        self.update_current_state_name(mode)
        self._sort_enable_table()

    def remove_from_enable_table(self, mode):
        self.debug_log("Removing mode: %s from enable_table", mode)

        try:
            del self.enable_table[mode]
            self._sort_enable_table()
        except KeyError:
            pass

    def update_current_state_name(self, mode):
        self.debug_log("Old current state name for mode %s: %s",
                       mode, self.enable_table[mode]['current_state_name'])

        try:
            self.enable_table[mode]['current_state_name'] = (
                self.enable_table[mode]['settings']['states']
                [self.player[self.enable_table[mode]['settings']
                          ['player_variable']]]['name'])

        except (TypeError, IndexError):
            self.enable_table[mode]['current_state_name'] = None

        self.debug_log("New current state name for mode %s: %s",
                       mode, self.enable_table[mode]['current_state_name'])

    def remove_active_profile(self, mode, **kwargs):
        del kwargs
        # this has the effect of changing out this mode's profile in the
        # enable_table with the next highest visible one.

        self.debug_log("Removing active profile for mode %s", mode)

        for k, v in self.enable_table.items():
            if (v['priority'] < self.enable_table[mode]['priority'] and
                    (v['enable'] or v['settings']['show_when_disabled'])):

                self.debug_log("Applying active profile from mode %s", k)

                self.update_enable_table(profile=v['profile'],
                                         enable=v['enable'],
                                         mode=mode)

                return

    def add_to_group(self, group):
        self.debug_log("Received request to add this shot to the %s group",
                       group)

        if isinstance(group, str):

            try:
                group = self.machine.shot_groups[group]
            except KeyError:
                self.debug_log("'%s' is not a valid shot_group name.",
                               group)
                return

        self.groups.add(group)

    def remove_from_group(self, group):
        self.debug_log("Received request to remove this shot from the %s "
                       "group", group)

        if isinstance(group, str):

            try:
                group = self.machine.shot_groups[group]
            except KeyError:
                self.debug_log("'%s' is not a valid shot_group name.",
                               group)
                return

        self.groups.discard(group)

    def _update_groups(self, profile, state):
        for group in self.groups:
            group.update_member_shot(shot=self, profile=profile, state=state)
