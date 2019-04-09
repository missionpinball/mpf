"""An achievement which can be reached in a pinball machine."""

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler

from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.devices.achievement_group import AchievementGroup


@DeviceMonitor(_state="state")
class Achievement(ModeDevice):

    """An achievement in a pinball machine.

    It is tracked per player and can automatically restore state on the next
    ball.
    """

    config_section = 'achievements'
    collection = 'achievements'
    class_label = 'achievement'
    allow_empty_configs = True

    def __init__(self, machine, name):
        """Initialise achievement."""
        super().__init__(machine, name)
        self._player = None
        self._mode = None
        self._show = None
        self._group_memberships = set()

    @property
    def state(self):
        """Return current state."""
        return self._state

    @property
    def _state(self):
        try:
            return self._player.achievements[self.name]
        except (AttributeError, KeyError):
            return ''

    @_state.setter
    def _state(self, value):
        self.debug_log('New state: %s', value)
        self._player.achievements[self.name] = value

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Validate and parse config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)

        states = ['disabled', 'enabled', 'started', 'stopped', 'selected',
                  'completed']

        for state in states:
            if not config['events_when_{}'.format(state)]:
                config['events_when_{}'.format(state)] = [
                    "achievement_{}_state_{}".format(self.name, state)]

        return config

    def enable(self):
        """Enable the achievement.

        It can only start if it was enabled before.
        """
        super().enable()
        if self._state in ("disabled", "selected", "started"):
            self._state = "enabled"
            self._run_state()

    @event_handler(5)
    def event_start(self, **kwargs):
        """Event handler for start event."""
        del kwargs
        self.start()

    def start(self):
        """Start achievement."""
        if self._state in ("enabled", "selected") or (
            self.config['restart_after_stop_possible'] and
                self._state == "stopped"):
            self._state = "started"
            self._run_state()

    @event_handler(4)
    def event_complete(self, **kwargs):
        """Event handler for complete event."""
        del kwargs
        self.complete()

    def complete(self):
        """Complete achievement."""
        if self._state in ("started", "selected"):
            self._state = "completed"
            self._run_state()

    @event_handler(2)
    def event_stop(self, **kwargs):
        """Event handler for stop event."""
        del kwargs
        self.stop()

    def stop(self):
        """Stop achievement."""
        if self._state in ("started", "selected"):
            self._state = "stopped"
            self._run_state()

    @event_handler(0)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable achievement."""
        if self._state in ("enabled", "selected") or (
            self.config['restart_after_stop_possible'] and
                self._state == "stopped"):
            self._state = "disabled"
            self._run_state()

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset the achievement to its initial state."""
        # if there is no player active
        if not self._player:
            return

        if self.config['enable_events']:
            self._state = "disabled"
        else:
            self._state = "enabled"

        self._run_state()

    @event_handler(9)
    def event_select(self, **kwargs):
        """Event handler for select event."""
        del kwargs
        self.select()

    def select(self):
        """Highlight (select) this achievement."""
        if not self._player:
            return

        if self._state == 'enabled':
            self._state = 'selected'

            self._run_state()

    def _run_state(self, restore=False):
        """Run shows and post events for current step."""
        for event in self.config['events_when_{}'.format(self._state)]:
            self.machine.events.post(event, restore=restore)
            '''event: achievement_(name)_state_(state)
            desc: Achievement (name) changed to state (state).

            Valid states are: disabled, enabled, started, completed

            This is only posted once per state. Its also posted on restart on the next ball to restore state.

            args:
                restore: true if this is reposted to restore state

            '''

        if self._show:
            self.debug_log('Stopping show: %s', self._show)
            self._show.stop()
            self._show = None

        show = self.config['show_when_' + self._state]

        if show:
            if show not in self.machine.shows:
                # don't want a "try:" here since it would swallow any errors
                # in show.play()
                raise KeyError("[achievements: {}: {}: {}] is not a valid show"
                               .format(self.name, 'show_when_' + self._state,
                                       show))

            self.debug_log('Playing show: %s. Priority: %s. Loops: -1. '
                           'Show tokens: %s', show, self._mode.priority,
                           self.config['show_tokens'])

            self._show = self.machine.shows[show].play(
                priority=self._mode.priority,
                loops=-1, sync_ms=self.config['sync_ms'],
                show_tokens=self.config['show_tokens'])

        for group in self._group_memberships:
            group.member_state_changed()

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Load device on mode start and restore state.

        Args:
            mode: mode which was contains the device
            player: player which is currently active
        """
        self._player = player
        self._mode = mode
        if not self._player.achievements:
            self._player.achievements = dict()      # type: ignore

        if self.name not in self._player.achievements:
            self.reset()
        else:
            self._restore_state()

    def _restore_state(self):
        if self._state == "started" and not (
                self.config['restart_on_next_ball_when_started']):
            self._state = "stopped"
        elif self._state == "enabled" and not (
                self.config['enable_on_next_ball_when_enabled']):
            self._state = "disabled"

        self._run_state(restore=True)

    def device_removed_from_mode(self, mode: Mode):
        """Mode ended.

        Args:
            mode: mode which stopped
        """
        del mode
        self._player = None
        self._mode = None
        if self._show:
            self._show.stop()
            self._show = None

    def add_control_events_in_mode(self, mode: Mode) -> None:
        """Override the default mode device behavior.

        Achievements use sophisticated logic to handle their mode-starting states
        during device_loaded_in_mode(). Therefore no default enabling is required.
        """
        pass

    def add_to_group(self, group):
        """Add this achievement to an achievement group.

        Args:
            group: The achievement group to add this achievement to.

        """
        assert isinstance(group, AchievementGroup)
        self._group_memberships.add(group)

    def remove_from_group(self, group):
        """Remove this achievement from an achievement group.

        Args:
            group: The achievement group to remove this achievement from.

        """
        assert isinstance(group, AchievementGroup)
        self._group_memberships.discard(group)
