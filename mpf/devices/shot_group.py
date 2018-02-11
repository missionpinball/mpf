"""Contains the ShotGroup base class."""

from collections import deque

from mpf.core.events import event_handler
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


class ShotGroup(ModeDevice):

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

        self.rotation_enabled = None
        self.profile = None
        self.rotation_pattern = None

    def add_control_events_in_mode(self, mode) -> None:
        """Remove enable here."""
        pass

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Add device in mode."""
        super().device_loaded_in_mode(mode, player)
        self._check_for_complete()
        self.profile = self.config['shots'][0].profile
        self.rotation_pattern = deque(self.profile.config['rotation_pattern'])
        self.rotation_enabled = not self.config['enable_rotation_events']
        for shot in self.config['shots']:
            self.machine.events.add_handler("{}_hit".format(shot.name), self._hit)

    def device_removed_from_mode(self, mode):
        """Disable device when mode stops."""
        super().device_removed_from_mode(mode)
        self.machine.events.remove_handler(self._hit)

    def _check_for_complete(self):
        """Check if all shots in this group are in the same state."""
        state = self.config['shots'][0].state_name
        for shot in self.config['shots']:
            if state != shot.state_name:
                # shots do not have a common state
                return

        # if we reached this point we got a common state

        self.debug_log(
            "Shot group is complete with state: %s", state)

        self.machine.events.post('{}_complete'.format(self.name), state=state)
        '''event: (shot_group)_complete
        desc: All the member shots in the shot group called (shot_group)
        are in the same state.

        args:
          state: name of the common state of all shots.
        '''

        self.machine.events.post('{}_{}_complete'.format(self.name, state))
        '''event: (shot_group)_(state)_complete
        desc: All the member shots in the shot group called (shot_group)
        are in the same state named (state).
        '''

    def enable(self, **kwargs):
        """Enable all member shots.

        Args:
            kwargs: passed to member shots
        """
        for shot in self.config['shots']:
            shot.enable(**kwargs)

    def disable(self, **kwargs):
        """Disable all member shots.

        Args:
            kwargs: passed to member shots
        """
        for shot in self.config['shots']:
            shot.disable(**kwargs)

    def reset(self, **kwargs):
        """Reset all member shots.

        Args:
            kwargs: passed to member shots
        """
        for shot in self.config['shots']:
            shot.reset(**kwargs)

    def _hit(self, advancing, **kwargs):
        """One of the member shots in this shot group was hit.

        Args:
            kwarg: {
                profile: the current profile of the member shot that was hit
                state: the current state of the member shot that was hit
                advancing: boolean of whether the state is advancing
            }
        """
        if advancing:
            self._check_for_complete()

        self.machine.events.post(self.name + '_hit')
        '''event: (shot_group)_hit
        desc: A member shots in the shot group called (shot_group)
        has been hit.
        '''
        self.machine.events.post("{}_{}_hit".format(self.name, kwargs['state']))
        '''event: (shot_group)_(state)_hit
        desc: A member shot with state (state) in the shot group (shot_group)
        has been hit.
        '''

    @event_handler(9)
    def enable_rotation(self, **kwargs):
        """Enable shot rotation.

        If disabled, rotation events do not actually rotate the shots.
        """
        del kwargs
        self.debug_log('Enabling rotation')
        self.rotation_enabled = True

    @event_handler(2)
    def disable_rotation(self, **kwargs):
        """Disable shot rotation.

        If disabled, rotation events do not actually rotate the shots.
        """
        del kwargs
        self.debug_log('Disabling rotation')
        self.rotation_enabled = False

    @event_handler(4)
    def rotate(self, direction=None, **kwargs):
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

        if not self.rotation_enabled:
            self.debug_log("Received rotation request. "
                           "Rotation Enabled: %s. Will NOT rotate",
                           self.rotation_enabled)

            return

        # shot_state_list is deque of tuples (state num, show step num)
        shot_state_list = deque()

        for shot in self.config['shots']:
            shot_state_list.append(shot.state)

        # figure out which direction we're going to rotate
        if not direction:
            direction = self.rotation_pattern[0]
            self.rotation_pattern.rotate(-1)
            self.debug_log("Since no direction was specified, pulling from"
                           " rotation pattern: '%s'", direction)

        # rotate that list
        if direction.lower() in ('right', 'r'):
            shot_state_list.rotate(1)
        else:
            shot_state_list.rotate(-1)

        # step through all our shots and update their states
        for i, shot in enumerate(self.config['shots']):
            shot.jump(state=shot_state_list[i], force=True)

    @event_handler(8)
    def rotate_right(self, mode=None, **kwargs):
        """Rotate the state of the shots to the right.

        This method is the same as calling rotate('right')

        Args:
            kwargs: unused

        """
        del kwargs
        self.rotate(direction='right', mode=mode)

    @event_handler(7)
    def rotate_left(self, mode=None, **kwargs):
        """Rotate the state of the shots to the left.

        This method is the same as calling rotate('left')

        Args:
            kwargs: unused

        """
        del kwargs
        self.rotate(direction='left', mode=mode)
