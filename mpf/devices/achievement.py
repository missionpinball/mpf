"""An achievement which can be reached in a pinball machine."""

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler

from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player


@DeviceMonitor("state", "selected")
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

    @property
    def state(self):
        """Return current state."""
        try:
            return self._player.achievements[self.name][0]
        except (AttributeError, KeyError):
            return None

    @state.setter
    def state(self, value):
        """Set current state."""
        try:
            self._player.achievements[self.name][0] = value
        except (AttributeError, KeyError):
            self._player.achievements[self.name] = [value, False]

    @property
    def can_be_selected_for_start(self):
        """Return if this achievement can be selected and started."""
        state = self.state
        return state == 'enabled' or (state == 'stopped' and self.config['restart_after_stop_possible'])

    @property
    def selected(self):
        """Return current selection state."""
        try:
            return self._player.achievements[self.name][1]
        except (AttributeError, KeyError):
            return False

    @selected.setter
    def selected(self, value):
        """Set current selected."""
        try:
            self._player.achievements[self.name][1] = value
        except (AttributeError, KeyError):
            self._player.achievements[self.name] = [None, value]

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Validate and parse config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)

        states = ['disabled', 'enabled', 'started', 'stopped', 'selected', 'completed']

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
        if self.state in ("disabled", "started"):
            self.state = "enabled"
            self._run_state()

    @event_handler(5)
    def event_start(self, **kwargs):
        """Event handler for start event."""
        del kwargs
        self.start()

    def start(self):
        """Start achievement."""
        if self.state == "enabled" or (
            self.config['restart_after_stop_possible'] and
                self.state == "stopped"):
            self.state = "started"
            self.selected = False
            self._run_state()

    @event_handler(4)
    def event_complete(self, **kwargs):
        """Event handler for complete event."""
        del kwargs
        self.complete()

    def complete(self):
        """Complete achievement."""
        if self.state == "started":
            self.state = "completed"
            self.selected = False
            self._run_state()

    @event_handler(2)
    def event_stop(self, **kwargs):
        """Event handler for stop event."""
        del kwargs
        self.stop()

    def stop(self):
        """Stop achievement."""
        if self.state == "started":
            self.state = "stopped"
            self.selected = False
            self._run_state()

    @event_handler(0)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable achievement."""
        if self.state == "enabled" or (
            self.config['restart_after_stop_possible'] and
                self.state == "stopped"):
            self.state = "disabled"
            self.selected = False
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

        self.selected = False

        if self.config['start_enabled'] is True:
            self.state = "enabled"
        elif self.config['start_enabled'] is False:
            self.state = "disabled"
        elif self.config['enable_events']:
            self.state = "disabled"
        else:
            self.state = "enabled"

        self._run_state()

    @event_handler(8)
    def event_unselect(self, **kwargs):
        """Event handler for unselect event."""
        del kwargs
        self.unselect()

    def unselect(self):
        """Remove highlight (unselect) this achievement."""
        if not self._player:
            return

        self.debug_log("Unselecting achievement")

        if self.selected:
            self.selected = False

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

        self.debug_log("Selecting achievement")

        if (self.state == 'enabled' or
                (self.config['restart_after_stop_possible'] and self.state == "stopped")) and not self.selected:
            self.selected = True
            self._run_state()

    def _run_state(self, restore=False):
        """Run shows and post events for current step."""
        self.machine.events.post("achievement_{}_changed_state".format(self.name), restore=restore,
                                 state=self.state, selected=self.selected)
        '''event: achievement_(name)_changed_state
        desc: Achievement (name) changed state.

        Valid states are: disabled, enabled, started, completed, stopped

        This is only posted once per state. Its also posted on restart on the next ball to restore state.

        args:
            restore: true if this is reposted to restore state
            state: Current state
            selected: Whatever this achievement is selected currently

        '''
        for event in self.config['events_when_{}'.format(self.state)]:
            self.machine.events.post(event, restore=restore, state=self.state, selected=self.selected)
            '''event: achievement_(name)_state_(state)
            desc: Achievement (name) changed to state (state).

            Valid states are: disabled, enabled, started, completed, stopped

            This is only posted once per state. Its also posted on restart on the next ball to restore state
            and when selection changes.

            args:
                restore: true if this is reposted to restore state
                state: Current state
                selected: Whatever this achievement is selected currently

            '''
        if self.selected:
            for event in self.config['events_when_selected']:
                self.machine.events.post(event, restore=restore, state=self.state, selected=self.selected)
                # same as above

        if self._show:
            self.debug_log('Stopping show: %s', self._show)
            self._show.stop()
            self._show = None

        if self.selected and self.config['show_when_selected']:
            show = self.config['show_when_selected']
        else:
            show = self.config['show_when_' + self.state]

        if show:
            self.debug_log('Playing show: %s. Priority: %s. Loops: -1. '
                           'Show tokens: %s', show.name, self._mode.priority,
                           self.config['show_tokens'])

            self._show = show.play(
                priority=self._mode.priority,
                loops=-1, sync_ms=self.config['sync_ms'],
                show_tokens=self.config['show_tokens'])

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Load device on mode start and restore state.

        Args:
        ----
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

        # state might have changed
        self.notify_virtual_change("selected", None, self.state)    # type: ignore

    def _restore_state(self):
        if self.state == "started" and not (
                self.config['restart_on_next_ball_when_started']):
            self.state = "stopped"
        elif self.state == "enabled" and not (
                self.config['enable_on_next_ball_when_enabled']):
            self.state = "disabled"
        else:
            # state might still have changed because of player change
            self.notify_virtual_change("state", None, self.state)

        self._run_state(restore=True)

    def device_removed_from_mode(self, mode: Mode):
        """Mode ended.

        Args:
        ----
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
