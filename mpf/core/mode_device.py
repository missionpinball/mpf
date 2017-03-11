"""Contains a class to implement mode devices."""
import abc

from mpf.core.device import Device
from mpf.core.mode import Mode
from mpf.core.player import Player


class ModeDevice(Device, metaclass=abc.ABCMeta):

    """A device in a mode."""

    def __init__(self, machine, name):
        """Initialise mode device."""
        super().__init__(machine, name)
        self.loaded_in_mode = None

    def device_added_to_mode(self, mode: Mode, player: Player):
        """Called when a device is created by a mode.

        Args:
            mode: Mode which loaded the device
            player: Current active player
        """
        del mode
        del player
        self._initialize()

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return False

    def overload_config_in_mode(self, mode, config):
        """Overload config in mode."""
        del mode
        del config
        raise AssertionError("Device {} cannot be overloaded.".format(self))

    def add_control_events_in_mode(self, mode):
        """Called on mode start if this device has any mode control events.

        Args:
            mode: Mode which loaded the device
        """
        if "enable_events" in self.config and not self.config['enable_events']:
            mode.add_mode_event_handler("mode_{}_started".format(mode.name),
                                        self.enable, priority=100)

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
            '{} does not have a device_removed_from_mode() method'.format(self))
