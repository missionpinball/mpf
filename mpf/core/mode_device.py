"""Contains a class to implement mode devices."""
import abc

from mpf.core.device import Device
from mpf.core.mode import Mode
from mpf.core.player import Player


class ModeDevice(Device, metaclass=abc.ABCMeta):

    """A device in a mode."""

    def device_added_to_mode(self, mode: Mode, player: Player):
        """Called when a device is created by a mode.

        Args:
            mode: Mode which loaded the device
            player: Current active player
        """
        del mode
        del player
        self._initialize()

    def add_control_events_in_mode(self, mode):
        """Called on mode start if this device has any control events in that mode.

        Args:
            mode: Mode which loaded the device
        """
        del mode
        if "enable_events" in self.config and not self.config['enable_events']:
            self.enable()

    def remove_control_events_in_mode(self):
        """Remove control events."""
        pass

    def device_removed_from_mode(self, mode):
        """Remove device because mode is unloading.

        Device object will continue to exist and may be added to the mode again later.

        Args:
            mode: Mode which stopped
        """
        del mode
        raise NotImplementedError(
            '{} does not have a device_removed_from_mode() method'.format(self.name))
