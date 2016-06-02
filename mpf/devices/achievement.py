"""An achievement which can be reached in a pinball machine."""
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player


class Achievement(ModeDevice):

    """An achievement in a pinball machine.

    It is tracked per player and can automatically restore state on the next ball.
    """

    config_section = 'achievements'
    collection = 'achievements'
    class_label = 'achievement'

    def __init__(self, machine, name):
        """Initialise achievement."""
        super().__init__(machine, name)
        self._player = None
        self._mode = None
        self._show = None

    @property
    def _state(self):
        return self._player.achievements[self.name]

    @_state.setter
    def _state(self, value):
        self._player.achievements[self.name] = value

    def enable(self, **kwargs):
        """Enable the achievement.

        It can only start if it was enabled before.
        """
        del kwargs
        if self._state == "disabled":
            self._state = "enabled"
            self._run_state()

    def start(self, **kwargs):
        """Start achievement."""
        del kwargs
        if self._state == "enabled" or (self.config['restart_after_stop_possible'] and self._state == "stopped"):
            self._state = "started"
            self._run_state()

    def complete(self, **kwargs):
        """Complete achievement."""
        del kwargs
        if self._state == "started":
            self._state = "completed"
            self._run_state()

    def stop(self, **kwargs):
        """Stop achievement."""
        del kwargs
        if self._state == "started":
            self._state = "stopped"
            self._run_state()

    def disable(self, **kwargs):
        """Disable achievement."""
        del kwargs
        if self._state == "enabled" or (self.config['restart_after_stop_possible'] and self._state == "stopped"):
            self._state = "disabled"
            self._run_state()

    def reset(self, **kwargs):
        """Reset the achievement to its initial state."""
        del kwargs
        # if there is no player active
        if not self._player:
            return

        if self.config['start_enabled']:
            self._state = "enabled"
        else:
            self._state = "disabled"

        self._run_state()

    def _run_state(self, restore=False):
        """Run shows and post events for current step."""
        if self.config['events_when_' + self._state]:
            events = self.config['events_when_' + self._state]
        else:
            events = ["achievement_{}_state_{}".format(self.name, self._state)]

        for event in events:
            self.machine.events.post(event, restore=restore)
            '''event: achievement_(name)_state_(state)
            desc: Achievement (name) changed to state (state).

            Valid states are: disabled, enabled, started, completed

            This is only posted once per state. Its also posted on restart on the next ball to restore state.

            args:
                restore: true if this is reposted to restore state

            '''

        show = self.config['show_when_' + self._state]
        if self._show:
            self._show.stop()
            self._show = None
        if show:
            self._show = self.machine.shows[show].play(
                priority=self._mode.priority,
                loops=-1,
                show_tokens=self.config['show_tokens'])

    def device_added_to_mode(self, mode: Mode, player: Player):
        """Load device on mode start and restore state.

        Args:
            mode: mode which was contains the device
            player: player which is currently active
        """
        super().device_added_to_mode(mode, player)
        self._player = player
        self._mode = mode
        if not self._player.achievements:
            self._player.achievements = dict()

        if self.name not in self._player.achievements:
            self.reset()
        else:
            self._restore_state()

    def _restore_state(self):
        if self._state == "started" and not self.config['restart_on_next_ball_when_started']:
            self._state = "stopped"
        elif self._state == "enabled" and not self.config['enable_on_next_ball_when_enabled']:
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
