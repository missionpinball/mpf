"""Contains the ShotGroup base class."""

from collections import deque

from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


class ShotGroup(ModeDevice, SystemWideDevice):

    """Represents a group of shots in a pinball machine by grouping together multiple `Shot` class devices.

    This is used so you get get
    "group-level" functionality, like shot rotation, shot group completion,
    etc. This would be used for a group of rollover lanes, a bank of standups,
    etc.
    """

    config_section = 'shot_groups'
    collection = 'shot_groups'
    class_label = 'shot_group'

    def __init__(self, machine, name):
        """Initialise shot group."""
        super().__init__(machine, name)

        self.rotation_enabled = True
        self._enabled = False

        # todo remove this hack
        self._created_system_wide = False

    @property
    def enabled(self):
        """Return true if enabled."""
        return self._enabled

    @classmethod
    def prepare_config(cls, config, is_mode_config):
        """Add default events if not in mode."""
        if not is_mode_config:
            # If this device is setup in a machine-wide config, make sure it has
            # a default enable event.
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

    def device_added_to_mode(self, mode, player):
        """Add device in mode."""
        super().device_added_to_mode(mode, player)

        # If there are no enable_events configured, then we enable this shot
        # group when its created on mode start

        if ((not mode.config['shot_groups'][self.name]['enable_events']) or
                'mode_{}_started'.format(mode.name) in
                mode.config['shot_groups'][self.name]['enable_events']):
            self.enable(mode)
        else:
            # manually call disable here so it disables the member shots
            self.disable(mode)

    def _enable_related_device_debugging(self):
        self.log.debug(
            "Enabling debugging for this shot groups's member shots")

        for shot in self.config['shots']:
            shot.enable_debugging()

    def _disable_related_device_debugging(self):
        for shot in self.config['shots']:
            shot.disable_debugging()

    def hit(self, mode, profile, state, **kwargs):
        """One of the member shots in this shot group was hit.

        Args:
            profile: String name of the active profile of the shot that
                was hit.
            mode: unused
            kwargs: unused
        """
        del mode
        del kwargs

        if not profile:
            raise AssertionError("Called hit without profile")

        if not self._enabled:
            return

        self.debug_log('Hit! Active profile: %s, Current state: %s',
                       profile, profile)

        self.machine.events.post(self.name + '_hit',
                                 profile=profile, state=state)
        '''event: (shot_group)_hit
        desc: A member shot in the shot group called (shot_group) was just hit.

        Note that there are three events posted when a member shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit
        '''

        self.machine.events.post(self.name + '_' + profile + '_hit',
                                 profile=profile, state=state)
        '''event: (shot_group)_(profile)_hit
        desc: A member shot in the shot group called (shot_group) was just hit
        with the profile called (profile) applied.

        Note that there are three events posted when a member shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''
        self.machine.events.post(self.name + '_' + profile + '_' + state +
                                 '_hit', profile=profile, state=state)
        '''event: (shot_group)_(profile)_(state)_hit
        desc: A member shot in the shot group called (shot_group) was just hit
        with the profile called (profile) applied in the current state called
        (state).

        Note that there are three events posted when a member shot is hit, each
        with variants of the shot name, profile, and current state,
        allowing you to key in on the specific granularity you need.

        Also remember that shots can have more than one active profile at a
        time (typically each associated with a mode), so a single hit to this
        shot might result in this event being posted multiple times with
        different (profile) values.

        args:
        profile: The name of the profile that was active when hit.
        state: The name of the state the profile was in when it was hit'''
    def enable(self, mode=None, profile=None, **kwargs):
        """Enable this shot group.

        Also enables all the shots in this group.
        """
        del kwargs

        if mode:
            self._enable_from_mode(mode, profile)
        else:
            self._enable_from_system_wide(profile)

        self._enabled = True

        self.rotation_enabled = not self.config['enable_rotation_events']

        self.debug_log('Enabling from mode: %s', mode)

    def _enable_from_mode(self, mode, profile=None):
        # If we weren't passed a profile, use the one from the mode config

        if not profile and mode.config['shot_groups'][self.name]['profile']:
            profile = mode.config['shot_groups'][self.name]['profile']

        for shot in self.config['shots']:
            if profile:
                # this is a passed profile or the profile in the shot group
                # in the mode config
                shot.update_profile(profile=profile, mode=mode, enable=True)

            else:
                shot.update_profile(mode=mode, enable=True)

            shot.register_group(self)

    def _enable_from_system_wide(self, profile=None):
        for shot in self.config['shots']:
            if 'profile' in self.config:
                shot.update_profile(profile=self.config['profile'],
                                    mode=None)
            shot.enable(profile=profile)
            shot.register_group(self)

    def disable(self, mode=None, **kwargs):
        """Disable this shot group.

        Also disables all the shots in this group.
        """
        del kwargs
        self._enabled = False
        self.debug_log('Disabling from mode: %s', mode)

        for shot in self.config['shots']:
            shot.disable(mode)
            shot.deregister_group(self)

    def enable_rotation(self, **kwargs):
        """Enable shot rotation.

        If disabled, rotation events do not actually rotate the shots.
        """
        del kwargs
        self.debug_log('Enabling rotation')
        self.rotation_enabled = True

    def disable_rotation(self, **kwargs):
        """Disable shot rotation.

        If disabled, rotation events do not actually rotate the shots.
        """
        del kwargs
        self.debug_log('Disabling rotation')
        self.rotation_enabled = False

    def reset(self, mode=None, **kwargs):
        """Reset each of the shots in this group back to the initial state in whatever shot profile they have applied.

        This is the same as calling each shot's reset() method one-by-one.
        """
        del kwargs
        self.debug_log('Resetting')
        for shot in self.config['shots']:
            shot.reset(mode)

    def remove_active_profile(self, mode, **kwargs):
        """Remove the current active profile from every shot in the group."""
        del kwargs
        self.debug_log('Removing active profile')
        for shot in self.config['shots']:
            shot.remove_active_profile(mode)

    def advance(self, steps=1, mode=None, force=False, **kwargs):
        """Advance the current active profile from every shot in the group one step forward."""
        del kwargs

        if not (self._enabled or force):
            return

        self.debug_log('Advancing')
        for shot in self.config['shots']:
            shot.advance(steps=steps, mode=mode, force=force)

    def rotate(self, direction=None, states=None,
               exclude_states=None, mode=None, **kwargs):
        """Rotate (or "shift") the state of all the shots in this group.

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
            states: A string of a state or a list of strings that represent the
                targets that will be selected to rotate. If None (default), then
                all targets will be included.
            exclude_states: A string of a state or a list of strings that
                controls whether any targets will *not* be rotated. (Any
                targets with an active profile in one of these states will not
                be included in the rotation. Default is None which means all
                targets will be rotated)
            kwargs: unused

        Note that this shot group must, and rotation_events for this
        shot group, must both be enabled for the rotation events to work.
        """
        del kwargs

        if not (self._enabled and self.rotation_enabled):
            self.debug_log("Received rotation request. "
                           "Rotation Enabled: %s. Will NOT rotate",
                           self.rotation_enabled)

            return

        # if we don't have states or exclude_states, we'll see if the first shot
        # in the group has them and use those. Since all the shots should have
        # the same profile applied, it's ok to just pick from the first one.

        if states:
            states = Util.string_to_lowercase_list(states)
        else:
            states = self.config['shots'][0].get_profile_by_key(
                'mode', mode)['settings']['state_names_to_rotate']

        if exclude_states:
            exclude_states = Util.string_to_lowercase_list(exclude_states)
        else:
            exclude_states = (
                self.config['shots'][0].get_profile_by_key(
                    'mode', mode)['settings']['state_names_to_not_rotate'])

        shot_list = list()

        # build of a list of shots we're actually going to rotate
        for shot in self.config['shots']:

            if ((not states or shot.get_profile_by_key(
                    'mode', mode)['current_state_name'] in states) and
                    shot.get_profile_by_key(
                    'mode', mode)['current_state_name'] not in exclude_states):
                shot_list.append(shot)

        # shot_state_list is deque of tuples (state num, show step num)
        shot_state_list = deque()

        for shot in shot_list:
            try:
                current_show_step = shot.get_profile_by_key('mode', mode)['running_show'].next_step_index
            except AttributeError:
                current_show_step = None

            shot_state_list.append(
                (shot.player[shot.get_profile_by_key('mode', mode)['settings']['player_variable']], current_show_step))

        if self.debug:
            self.log.debug('Rotating. Mode: %s, Direction: %s, Include states:'
                           ' %s, Exclude states: %s, Shots to be rotated: %s',
                           mode, direction, states,
                           exclude_states, [x.name for x in shot_list])

            for shot in shot_list:
                shot.log.debug("This shot is part of a rotation event. Current"
                               " state: %s", shot.get_profile_by_key('mode', mode)['current_state_name'])

        # figure out which direction we're going to rotate
        if not direction:
            direction = shot_list[0].get_profile_by_key(
                'mode', mode)['settings']['rotation_pattern'][0]
            shot_list[0].get_profile_by_key(
                'mode', mode)['settings']['rotation_pattern'].rotate(-1)

            self.debug_log("Since no direction was specified, pulling from"
                           " rotation pattern: '%s'", direction)

        # rotate that list
        if direction == 'right':
            shot_state_list.rotate(1)
        else:
            shot_state_list.rotate(-1)

        # step through all our shots and update their states
        for i, shot in enumerate(shot_list):
            shot.jump(mode=mode, state=shot_state_list[i][0],
                      show_step=shot_state_list[i][1], force=True)

    def rotate_right(self, mode=None, **kwargs):
        """Rotate the state of the shots to the right.

        This method is the same as calling rotate('right')

        Args:
            kwargs: unused

        """
        del kwargs
        self.rotate(direction='right', mode=mode)

    def rotate_left(self, mode=None, **kwargs):
        """Rotate the state of the shots to the left.

        This method is the same as calling rotate('left')

        Args:
            kwargs: unused

        """
        del kwargs
        self.rotate(direction='left', mode=mode)

    def check_for_complete(self, mode):
        """Check all the shots in this shot group.

        If they are all in the same state, then a complete event is posted.
        """
        # TODO should be made to work for lower priority things too?
        if not self._enabled:
            return

        shot_states = set()

        self.debug_log("Checking for complete. mode: %s", mode)

        for shot in self.config['shots']:

            mode_state = shot.get_profile_by_key('mode', mode)

            if mode_state:
                shot_states.add((mode_state['profile'],
                                 mode_state['current_state_name']))

            else:
                self.debug_log("Shot %s is not used in this mode. Aborting"
                               " check for complete", shot)
                return

        if len(shot_states) == 1:
            profile, state = shot_states.pop()

            self.debug_log(
                "Shot group is complete with profile :%s, state:"
                "%s", profile, state)

            self.machine.events.post(self.name + '_complete')
            '''event: (shot_group)_complete
            desc: All the member shots in the shot group called (shot_group)
            are in the same state.
            '''

            self.machine.events.post(self.name + '_' + profile + '_complete')
            '''event: (shot_group)_(profile)_complete
            desc: All the member shots in the shot group called (shot_group)
            with the profile called (profile) are in the same state.
            '''

            self.machine.events.post(self.name + '_' + profile + '_' + state +
                                     '_complete')
            '''event: (shot_group)_(profile)_(state)_complete
            desc: All the member shots in the shot group called (shot_group)
            with the profile called (profile) are in the same state with the
            name (state).
            '''

    def add_control_events_in_mode(self, mode):
        """Add control events in mode."""
        # called if any control_events for this shot_group exist in the mode
        # config, regardless of whether or not the shot_group device was
        # initially created in this mode
        for shot in self.config['shots']:
            if not shot.get_profile_by_key('mode', mode):

                self.debug_log('Control events found in %s '
                               'config. Adding profile list entries to '
                               'member shots', mode)

                enable = not self.config['enable_events']

                if self.config['profile']:
                    profile = self.config['profile']
                else:
                    profile = shot.config['profile']

                shot.update_profile(profile=profile, enable=enable, mode=mode)

    def device_removed_from_mode(self, mode):
        """Disable device when mode stops."""
        del mode
        if self._created_system_wide:
            return
        self.debug_log("Removing this shot group")
        self._enabled = False
