"""Implements enable and disable events for devices."""
import abc

from mpf.core.events import event_handler

from mpf.core.device import Device
from mpf.core.machine import MachineController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.mode import Mode
    from mpf.core.player import Player


class EnableDisableMixin(Device, metaclass=abc.ABCMeta):

    """Implements enable and disable_events."""

    def __init__(self, machine: MachineController, name: str) -> None:
        """Remember the enable state."""
        self._enabled = None    # type: bool
        super().__init__(machine, name)

    def _enable(self):
        """Enable the device.

        This can be caused by a mode restore, initial enable at boot or by an
        enable_event.
        """
        pass

    def _disable(self):
        """Disable the device.

        This can be caused by a mode stop or by an disable_event.
        """
        pass

    @event_handler(100)
    def enable(self, **kwargs) -> None:
        """Enable device."""
        del kwargs
        if self._enabled is True:
            return
        self._enabled = True
        self._enable()

    def add_control_events_in_mode(self, mode) -> None:
        """Remove enable here."""
        pass

    @event_handler(0)
    def disable(self, **kwargs):
        """Disable device."""
        del kwargs
        if self._enabled is False:
            return
        self._enabled = False
        self._disable()

    def _load_enable_based_on_config_default(self) -> None:
        """Load default enable state from config."""
        if 'start_enabled' in self.config and self.config['start_enabled'] is True:
            start_enabled = True
        elif 'start_enabled' in self.config and self.config['start_enabled'] is False:
            start_enabled = False
        elif 'enable_events' in self.config:
            start_enabled = not self.config['enable_events']
        else:
            start_enabled = False

        if start_enabled:
            self._enable()
            self._enabled = True
        else:
            self._enabled = False

    @property
    def enabled(self):
        """Return true if enabled."""
        return self._enabled

    def _load_enable_from_player(self) -> None:
        """Load enable from player."""
        if self._enabled is None:
            self._load_enable_based_on_config_default()

    def device_loaded_in_mode(self, mode: "Mode", player: "Player") -> None:
        """Check enable on mode start."""
        del mode
        del player
        if self._enabled is None:
            if 'persist_enable' in self.config and self.config['persist_enable']:
                self._load_enable_from_player()
            else:
                self._load_enable_based_on_config_default()

    def device_removed_from_mode(self, mode) -> None:
        """Forget enable state."""
        del mode
        self._enabled = None

    def device_added_system_wide(self) -> None:
        """Check enable on boot."""
        self._load_enable_based_on_config_default()
