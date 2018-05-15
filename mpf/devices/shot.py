"""A shot in MPF."""

import uuid
from copy import copy, deepcopy

from mpf.core.enable_disable_mixin import EnableDisableMixin

import mpf.core.delays
from mpf.core.events import event_handler
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player


class Shot(EnableDisableMixin, ModeDevice):

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
        self.active_delays = set()
        self.running_show = None
        self._handlers = []

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Add device to a mode that was already started.

        Automatically enables the shot and calls the the method
        that's usually called when a player's turn starts since that was missed
        since the mode started after that.
        """
        super().device_loaded_in_mode(mode, player)
        self._update_show()

    def _initialize(self):
        for switch in self.config['switch']:
            if switch not in self.config['switches']:
                self.config['switches'].append(switch)

    def _register_switch_handlers(self):
        self._handlers = []
        for switch in self.config['switches']:
            self._handlers.append(self.machine.events.add_handler("{}_active".format(switch.name),
                                                                  self.hit, priority=self.mode.priority,
                                                                  blocking_facility="shot"))

        for switch in list(self.config['delay_switch'].keys()):
            self._handlers.append(self.machine.events.add_handler("{}_active".format(switch.name),
                                                                  self._delay_switch_hit,
                                                                  switch_name=switch.name,
                                                                  priority=self.mode.priority,
                                                                  blocking_facility="shot"))

    def _remove_switch_handlers(self):
        self.delay.clear()
        self.active_delays = set()

        self.machine.events.remove_handlers_by_keys(self._handlers)
        self._handlers = []

    @event_handler(6)
    def advance(self, force=False, **kwargs) -> bool:
        """Advance a shot profile forward.

        If this profile is at the last step and configured to loop, it will
        roll over to the first step. If this profile is at the last step and not
        configured to loop, this method has no effect.
        """
        del kwargs

        if not self.enabled and not force:
            return False

        if not self.player:
            # no player no state
            return False

        profile_name = self.config['profile'].name
        state = self._get_state()

        self.debug_log("Advancing 1 step. Profile: %s, "
                       "Current State: %s", profile_name, state)

        if state + 1 >= len(self.config['profile'].config['states']):

            if self.config['profile'].config['loop']:
                self._set_state(0)

            else:
                return False
        else:
            self.debug_log("Advancing shot by one step.")
            self._set_state(state + 1)

        self._update_show()
        return True

    def _stop_show(self):
        if not self.running_show:
            return
        self.running_show.stop()
        self.running_show = None

    @property
    def state_name(self):
        """Return current state name."""
        if not self.player:
            # no player no state
            return "None"
        return self.config['profile'].config['states'][self._get_state()]['name']

    @property
    def state(self):
        """Return current state index."""
        return self._get_state()

    @property
    def profile_name(self):
        """Return profile name."""
        return self.config['profile'].name

    @property
    def profile(self):
        """Return profile."""
        return self.config['profile']

    def _get_state(self):
        if not self.player:
            return 0
        return self.player["shot_{}".format(self.name)]

    def _set_state(self, state):
        self.player["shot_{}".format(self.name)] = state

    def _get_profile_settings(self):
        state = self._get_state()
        return self.profile.config['states'][state]

    def _update_show(self):
        if not self.enabled and not self.profile.config['show_when_disabled']:
            self._stop_show()
            return

        state = self._get_state()
        state_settings = self.profile.config['states'][state]

        if state_settings['show']:  # there's a show specified this state
            self._play_show(settings=state_settings)

        elif self.profile.config['show']:
            # no show for this state, but we have a profile root show
            self._play_show(settings=state_settings, start_step=state + 1)

        # if neither if/elif above happens, it means the current step has no
        # show but the previous step had one. We stop the previous show if there is one
        elif self.running_show:
            self._stop_show()

    def _play_show(self, settings, start_step=None):
        s = deepcopy(settings)
        if settings['show']:
            show_name = settings['show']
            if s['manual_advance'] is None:
                s['manual_advance'] = False

        else:
            show_name = self.profile.config['show']
            if s['manual_advance'] is None:
                s['manual_advance'] = True

        s['show_tokens'].update(self.config['show_tokens'])
        s['priority'] += self.mode.priority
        if not start_step:
            start_step = s.pop('start_step')
        else:
            s.pop('start_step')

        s.pop('show')
        s.pop('name')

        self.debug_log("Playing show: %s. %s", show_name, s)

        show_config = self.machine.show_controller.create_show_config(show_name, **s)
        self.running_show = self.machine.show_controller.replace_or_advance_show(self.running_show, show_config,
                                                                                 start_step)

    def device_removed_from_mode(self, mode):
        """Remove this shot device.

        Destroys it and removes it from the shots collection.
        """
        super().device_removed_from_mode(mode)
        self._remove_switch_handlers()
        if self.running_show:
            self.running_show.stop()
            self.running_show = None

    @event_handler(5)
    def hit(self, **kwargs):
        """Advance the currently-active shot profile.

        Note that the shot must be enabled in order for this hit to be
        processed.
        """
        # mark the playfield active no matter what
        self.config['playfield'].mark_playfield_active_from_device_action()

        if not self.enabled or not self.player:
            return None

        # Stop if there is an active delay but no sequence
        if self.active_delays:
            return None

        profile_settings = self._get_profile_settings()

        if not profile_settings:
            return None

        state = profile_settings['name']

        self.debug_log("Hit! Profile: %s, State: %s",
                       self.profile_name, state)

        if self.profile.config['advance_on_hit']:
            self.debug_log("Advancing shot because advance_on_hit is True.")
            advancing = self.advance()
        else:
            self.debug_log('Not advancing shot')
            advancing = False

        self._notify_monitors(self.config['profile'].name, state)

        self.machine.events.post('{}_hit'.format(self.name),
                                 profile=self.profile_name, state=state, advancing=advancing)
        '''event: (shot)_hit
        desc: The shot called (shot) was just hit.

        Note that there are four events posted when a shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''

        self.machine.events.post('{}_{}_hit'.format(self.name, self.profile_name),
                                 profile=self.profile_name, state=state, advancing=advancing)
        '''event: (shot)_(profile)_hit
        desc: The shot called (shot) was just hit with the profile (profile)
        active.

        Note that there are four events posted when a shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''

        self.machine.events.post('{}_{}_{}_hit'.format(self.name, self.profile_name, state),
                                 profile=self.profile_name, state=state, advancing=advancing)
        '''event: (shot)_(profile)_(state)_hit
        desc: The shot called (shot) was just hit with the profile (profile)
        active in the state (state).

        Note that there are four events posted when a shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) and (state) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''

        self.machine.events.post('{}_{}_hit'.format(self.name, state),
                                 profile=self.profile_name, state=state, advancing=advancing)
        '''event: (shot)_(state)_hit
        desc: The shot called (shot) was just hit while in the profile (state).

        Note that there are four events posted when a shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) and (state) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''

        if self.profile.config['block']:
            min_priority = kwargs.get("_min_priority", {"all": 0})
            min_shots = min_priority.get("shot", 0)
            min_priority["shot"] = self.mode.priority if self.mode.priority > min_shots else min_shots
            return {"_min_priority": min_priority}

        return None

    def _notify_monitors(self, profile, state):
        if Shot.monitor_enabled and "shots" in self.machine.monitors:
            for callback in self.machine.monitors['shots']:
                callback(name=self.name, profile=profile, state=state)

    @event_handler(4)
    def _delay_switch_hit(self, switch_name, **kwargs):
        del kwargs
        if not self.enabled:
            return

        self.delay.reset(name=switch_name + '_delay_timer',
                         ms=self.config['delay_switch']
                                       [self.machine.switches[switch_name]],
                         callback=self._release_delay,
                         switch=switch_name)

        self.active_delays.add(switch_name)

    def _release_delay(self, switch):
        self.active_delays.remove(switch)

    def jump(self, state, force=True):
        """Jump to a certain state in the active shot profile.

        Args:
            state: int of the state number you want to jump to. Note that states
                are zero-based, so the first state is 0.
            show_step: The step number that the associated light script
                should start playing at. Useful with rotations so this shot can
                pick up right where it left off. Default is 1 (the first step
                in the show)

        """
        self.debug_log("Received jump request. State: %s, Force: %s", state, force)

        if not self.enabled and not force:
            self.debug_log("Profile is disabled and force is False. Not jumping")
            return

        if not self.player:
            # no player no state
            return

        current_state = self._get_state()

        if state == current_state:
            self.debug_log("Shot is already in the jump destination state")
            return

        self.debug_log("Jumping to profile state '%s'", state)

        self._set_state(state)

        self._update_show()

    @event_handler(1)
    def reset(self, **kwargs):
        """Reset the shot profile for the passed mode back to the first state (State 0) and reset all sequences."""
        del kwargs
        self.debug_log("Resetting.")

        self.jump(state=0)

    def _enable(self):
        super()._enable()
        self._register_switch_handlers()
        self._update_show()

    def _disable(self):
        super()._disable()
        self._remove_switch_handlers()
        self._update_show()
