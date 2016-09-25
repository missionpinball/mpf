"""Controller for all service functionality.

Controller provides all service information and can perform service tasks. Displaying the information is performed by
the service mode or other components.
"""
import logging
from collections import namedtuple

from mpf.core.mpf_controller import MpfController

CoilMap = namedtuple("CoilMap", ["board", "coil"])


class ServiceController(MpfController):

    """Provides all service information and can perform service tasks."""

    def __init__(self, machine):
        """Initialise service controller."""
        super().__init__(machine)
        self._enabled = False
        self.log = logging.getLogger("ServiceController")

    def is_in_service(self) -> bool:
        """Return true if in service mode."""
        return self._enabled

    def start_service(self):
        """Start service mode."""
        if self.is_in_service():
            raise AssertionError("Already in service mode!")
        self._enabled = True

        self.log.info("Entered service mode. Resetting game if running. Resetting hardware interface now.")
        # this will stop attact and game mode
        for mode in self.machine.modes.values():
            if not mode.active or mode.name == "service":
                continue
            mode.stop()

        self.machine.events.post("service_mode_entered")

        # TODO: reset hardware interface

    def stop_service(self):
        """Stop service mode."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")
        self._enabled = False

        # this event starts attract mode again
        self.machine.events.post("service_mode_exited")
        self.machine.reset()

    def get_switch_map(self):
        """Return a map of all switches in the machine."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")

    def get_coil_map(self) -> [CoilMap]:
        """Return a map of all coils in the machine."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")
        coil_map = []
        for coil in self.machine.coils.values():
            coil_map.append(CoilMap(coil.hw_driver.get_board_name(), coil))

        # sort by board + driver number
        coil_map.sort(key=lambda x: x[0] + str(x[1].hw_driver.number))
        return coil_map
