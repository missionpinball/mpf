"""Implements enable and disable events for devices."""
import abc
import asyncio

from mpf.core.device_monitor import DeviceMonitor

from mpf.core.events import event_handler

from mpf.core.mode_device import ModeDevice
from mpf.core.machine import MachineController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.mode import Mode


@DeviceMonitor("enabled")
class EnableDisableMixin(ModeDevice, metaclass=abc.ABCMeta):

    """Implements enable and disable_events."""

    __slots__ = ["_enabled", "player"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Remember the enable state."""
        self._enabled = None    # type: bool
        self.player = None
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

    def enable(self) -> None:
        """Enable device."""
        if self.enabled is True:
            return
        self.enabled = True
        self.notify_virtual_change("enabled", False, True)
        self._enable()

    def add_control_events_in_mode(self, mode) -> None:
        """Remove enable here."""
        pass

    @event_handler(0)
    def event_disable(self, **kwargs):
        """Handle disable control event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable device."""
        if self.enabled is False:
            return
        self.enabled = False
        self.notify_virtual_change("enabled", True, False)
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
            self.enabled = True
        else:
            self.enabled = False

    @property
    def enabled(self):
        """Return true if enabled."""
        if 'persist_enable' in self.config and self.config['persist_enable']:
            # in case the mode is not running the device is disabled
            if not self.player:
                return False
            return self.player["{}_{}_enabled".format(self.class_label, self.name)]
        else:
            return self._enabled

    @enabled.setter
    def enabled(self, value):
        """Set enabled enabled."""
        if 'persist_enable' in self.config and self.config['persist_enable']:
            self.player["{}_{}_enabled".format(self.class_label, self.name)] = value
        else:
            self._enabled = value

    @property
    def persist_enabled(self):
        """Return if enabled is persisted."""
        return 'persist_enable' in self.config and self.config['persist_enable']

    def device_loaded_in_mode(self, mode: "Mode", player) -> None:
        """Check enable on mode start."""
        super().device_loaded_in_mode(mode, player)
        self.player = player
        if self.persist_enabled:
            if not player.is_player_var("{}_{}_enabled".format(self.class_label, self.name)):
                self._load_enable_based_on_config_default()
            elif self.enabled:
                self._enable()
        else:
            self._load_enable_based_on_config_default()

    def device_removed_from_mode(self, mode) -> None:
        """Forget enable state."""
        del mode
        self._disable()
        self.player = None
        self._enabled = None

    @asyncio.coroutine
    def device_added_system_wide(self) -> None:
        """Check enable on boot."""
        yield from super().device_added_system_wide()
        self._load_enable_based_on_config_default()
