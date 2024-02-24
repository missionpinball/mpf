"""Contains a class to implement mode devices."""
from typing import Optional

import abc

from mpf.core.device import Device
from mpf.core.events import event_handler
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.player import Player


class ModeDevice(Device, metaclass=abc.ABCMeta):

    """A device in a mode."""

    __slots__ = ["mode"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """initialize mode device."""
        super().__init__(machine, name)
        self.mode = None    # type: Optional[Mode]

    async def device_added_to_mode(self, mode: Mode) -> None:
        """Add device to a running mode.

        Args:
        ----
            mode: Mode which loaded the device
        """
        del mode
        await self._initialize()

    def device_loaded_in_mode(self, mode: Mode, player: Player) -> None:
        """Load device in running mode.

        The mode just started.

        Args:
        ----
            mode: Mode which loaded the device
            player: Current active player
        """
        del player
        self.mode = mode

    @property
    def can_exist_outside_of_game(self) -> bool:
        """Return true if this device can exist outside of a game."""
        return False

    def overload_config_in_mode(self, mode: Mode, config: dict) -> None:
        """Overload config in mode."""
        del mode
        del config
        raise AssertionError("Device {} cannot be overloaded.".format(self))

    @event_handler(20)
    def event_enable(self, **kwargs):
        """Event handler for enable event."""
        del kwargs
        self.enable()

    def enable(self) -> None:
        """Enable handler."""

    def add_control_events_in_mode(self, mode: Mode) -> None:
        """Add control events in mode if this device has any mode control events.

        Args:
        ----
            mode: Mode which loaded the device
        """
        if "enable_events" in self.config and not self.config['enable_events']:
            mode.add_mode_event_handler("mode_{}_started".format(mode.name),
                                        self.event_enable, priority=100)

    def remove_control_events_in_mode(self) -> None:
        """Remove control events."""

    def device_removed_from_mode(self, mode: Mode) -> None:
        """Remove device because mode is unloading.

        Device object will continue to exist and may be added to the mode again later.

        Args:
        ----
            mode: Mode which stopped
        """
        del mode
        self.mode = None
