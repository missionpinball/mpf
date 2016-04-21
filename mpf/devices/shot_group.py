""" Contains the ShotGroup base class."""

from collections import deque

from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


class ShotGroup(ModeDevice, SystemWideDevice):
    """Represents a group of shots in a pinball machine by grouping
    together multiple `Shot` class devices. This is used so you get get
    "group-level" functionality, like shot rotation, shot group completion,
    etc. This would be used for a group of rollover lanes, a bank of standups,
    etc.

    """
    config_section = 'shot_groups'
    collection = 'shot_groups'
    class_label = 'shot_group'

    def __init__(self, machine, name):

        super().__init__(machine, name)

        self.rotation_enabled = True
        self._enabled = False

    @property
    def enabled(self):
        return self._enabled

    def prepare_config(self, config, is_mode_config):
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
        # Called when a device is added system wide
        super().device_added_system_wide()

        if 'profile' in self.config:
            for shot in self.config['shots']:
                shot.update_enable_table(profile=self.config['profile'],
                                         mode=None)

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

        if not self._enabled:
            return

        self.debug_log('Hit! Active profile: %s, Current state: %s',
                       profile, profile)

        self.machine.events.post(self.name + '_hit',
                                 profile=profile, state=state)

        self.machine.events.post(self.name + '_' + profile + '_hit',
                                 profile=profile, state=state)

        self.machine.events.post(self.name + '_' + profile + '_' + state +
                                 '_hit', profile=profile, state=state)

    def enable(self, mode=None, profile=None, **kwargs):
        """Enables this shot group. Also enables all the shots in this
        group.

        """
        del kwargs

        if mode:
            self._enable_from_mode(mode, profile)
        else:
            self._enable_from_systemwide(profile)

        self._enabled = True
        self.debug_log('Enabling from mode: %s', mode)

        for shot in self.config['shots']:
            shot.enable(mode)
            shot.add_to_group(self)

    def _enable_from_mode(self, mode, profile=None):
        # If we weren't passed a profile, use the one from the mode config
        if not profile and mode.config['shot_groups'][self.name]['profile']:
            profile = mode.config['shot_groups'][self.name]['profile']

        for shot in self.config['shots']:
            if mode not in shot.enable_table:
                # if the mode is not in the shot's enable_table, that means we
                # have no entry for this shot in this mode config. Therefore
                # there is no chance of a blank enable_events:, which means we
                # want to enable this shot.

                if profile:
                    shot.update_enable_table(profile=profile,
                                             enable=True,
                                             mode=mode)

                else:
                    shot.update_enable_table(profile=shot.config['profile'],
                                             enable=True,
                                             mode=mode)

    def _enable_from_systemwide(self, profile=None):
        for shot in self.config['shots']:
            shot.enable(profile=profile)
            shot.add_to_group(self)

    def disable(self, mode=None, **kwargs):
        """Disables this shot group. Also disables all the shots in this
        group.

        """
        del kwargs
        self._enabled = False
        self.debug_log('Disabling from mode: %s', mode)

        for shot in self.config['shots']:
            shot.disable(mode)
            shot.remove_from_group(self)

    def enable_rotation(self, **kwargs):
        """Enables shot rotation. If disabled, rotation events do not actually
        rotate the shots.

        """
        del kwargs
        self.debug_log('Enabling rotation')
        self.rotation_enabled = True

    def disable_rotation(self, **kwargs):
        """Disables shot rotation. If disabled, rotation events do not actually
        rotate the shots.

        """
        del kwargs
        self.debug_log('Disabling rotation')
        self.rotation_enabled = False

    def reset(self, mode=None, **kwargs):
        """Resets each of the shots in this group back to the initial state in
        whatever shot profile they have applied. This is the same as calling
        each shot's reset() method one-by-one.

        """
        del kwargs
        self.debug_log('Resetting')
        for shot in self.config['shots']:
            shot.reset(mode)

    def remove_active_profile(self, mode, **kwargs):
        """Removes the current active profile from every shot in the group.

        """
        del kwargs
        self.debug_log('Removing active profile')
        for shot in self.config['shots']:
            shot.remove_active_profile(mode)

    def advance(self, mode=None, force=False, **kwargs):
        """Advances the current active profile from every shot in the group
        one step forward.

        """
        del kwargs

        if not (self._enabled or force):
            return

        self.debug_log('Advancing')
        for shot in self.config['shots']:
            shot.advance(mode)

    def rotate(self, direction=None, states=None,
               exclude_states=None, mode=None, **kwargs):
        """Rotates (or "shifts") the state of all the shots in this group.
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
            states = self.config['shots'][0].enable_table[mode]['settings'][
                'state_names_to_rotate']

        if exclude_states:
            exclude_states = Util.string_to_lowercase_list(exclude_states)
        else:
            exclude_states = (
                self.config['shots'][0].enable_table[mode]['settings'][
                    'state_names_to_not_rotate'])

        shot_list = list()

        # build of a list of shots we're actually going to rotate
        for shot in self.config['shots']:

            if ((not states or shot.enable_table[mode]['current_state_name'] in states) and
                    shot.enable_table[mode]['current_state_name'] not in exclude_states):
                shot_list.append(shot)

        # shot_state_list is deque of tuples (state num, light show step num)
        shot_state_list = deque()

        for shot in shot_list:

            try:
                current_state = shot.running_light_show.current_location

            except AttributeError:
                current_state = -1

            shot_state_list.append(
                    (shot.player[shot.enable_table[mode]['settings'][
                        'player_variable']],
                     current_state))

        if self.debug:
            self.log.debug('Rotating. Mode: %s, Direction: %s, Include states:'
                           ' %s, Exclude states: %s, Shots to be rotated: %s',
                           mode, direction, states,
                           exclude_states, [x.name for x in shot_list])

            for shot in shot_list:
                shot.log.debug("This shot is part of a rotation event. Current"
                               " state: %s",
                               shot.enable_table[mode]['current_state_name'])

        # figure out which direction we're going to rotate
        if not direction:
            direction = shot_list[0].enable_table[mode]['settings']['rotation_pattern'][0]
            shot_list[0].enable_table[mode]['settings']['rotation_pattern'].rotate(-1)

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
                      show_step=shot_state_list[i][1])

    def rotate_right(self, mode=None, **kwargs):
        """Rotates the state of the shots to the right. This method is the
        same as calling rotate('right')

        Args:
            kwargs: unused

        """
        del kwargs
        self.rotate(direction='right', mode=mode)

    def rotate_left(self, mode=None, **kwargs):
        """Rotates the state of the shots to the left. This method is the
        same as calling rotate('left')

        Args:
            kwargs: unused

        """
        del kwargs
        self.rotate(direction='left', mode=mode)

    def check_for_complete(self, mode):
        """Checks all the shots in this shot group. If they are all in the
        same state, then a complete event is posted.

        """

        # TODO should be made to work for lower priority things too?

        if not self._enabled:
            return

        shot_states = set()

        self.debug_log("Checking for complete. mode: %s", mode)

        for shot in self.config['shots']:

            mode_state = shot.get_mode_state(mode)

            if mode_state:
                shot_states.add(mode_state)

                self.debug_log("%s state: %s", shot.name,
                               shot.get_mode_state(mode))

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
            self.machine.events.post(self.name + '_' + profile + '_complete')
            self.machine.events.post(self.name + '_' + profile + '_' + state +
                                     '_complete')

    def device_added_to_mode(self, mode, player):
        super().device_added_to_mode(mode, player)

        # If there are no enable_events configured, then we enable this shot
        # group when its created on mode start
        if not mode.config['shot_groups'][self.name]['enable_events']:
            self.enable(mode)

    def control_events_in_mode(self, mode):
        # called if any control_events for this shot_group exist in the mode
        # config, regardless of whether or not the shot_group device was
        # initially created in this mode
        for shot in self.config['shots']:
            if mode not in shot.enable_table:

                self.debug_log('Control events found in %s '
                               'config. Adding enable_table entries to '
                               'member shots', mode)

                enable = not self.config['enable_events']

                if self.config['profile']:
                    profile = self.config['profile']
                else:
                    profile = shot.config['profile']

                shot.update_enable_table(profile=profile,
                                         enable=enable,
                                         mode=mode)

    def remove(self):
        self.debug_log("Removing this shot group")
        self._enabled = False
        del self.machine.shot_groups[self.name]
