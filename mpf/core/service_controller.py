"""Controller for all service functionality.

Controller provides all service information and can perform service tasks. Displaying the information is performed by
the service mode or other components.
"""
import logging
import re
from collections import namedtuple

from typing import List
import asyncio

from mpf.core.mpf_controller import MpfController

SwitchMap = namedtuple("SwitchMap", ["board", "switch"])
CoilMap = namedtuple("CoilMap", ["board", "coil"])
LightMap = namedtuple("LightMap", ["board", "light"])


class ServiceController(MpfController):

    """Provides all service information and can perform service tasks."""

    __slots__ = ["_enabled"]

    config_name = "service_controller"

    def __init__(self, machine):
        """Initialise service controller."""
        super().__init__(machine)
        self._enabled = False
        self.configure_logging("service")

    @staticmethod
    def _natural_key_sort(string_):
        """Sort by natural keys like humans do.

        See http://www.codinghorror.com/blog/archives/001018.html.
        """
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

    def is_in_service(self) -> bool:
        """Return true if in service mode."""
        return self._enabled

    def start_service(self):
        """Start service mode."""
        if self.is_in_service():
            raise AssertionError("Already in service mode!")
        self._enabled = True

        self.info_log("Entered service mode. Resetting game if running. Resetting hardware interface now.")
        # this will stop attact and game mode
        for mode in self.machine.modes.values():
            if not mode.active or mode.name in ["service", "game"]:
                continue
            mode.stop()

        # explicitly stop game last
        if self.machine.modes.game.active:
            self.machine.modes.game.stop()

        self.machine.events.post("service_mode_entered")

        # TODO: reset hardware interface

    @asyncio.coroutine
    def stop_service(self):
        """Stop service mode."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")
        self._enabled = False

        # this event starts attract mode again
        self.machine.events.post("service_mode_exited")
        yield from self.machine.reset()

    def get_switch_map(self):
        """Return a map of all switches in the machine."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")

        switch_map = []
        for switch in self.machine.switches.values():
            switch_map.append(SwitchMap(switch.hw_switch.get_board_name(), switch))

        # sort by board + driver number
        switch_map.sort(key=lambda x: (self._natural_key_sort(x[0]),
                                       self._natural_key_sort(str(x[1].hw_switch.number))))
        return switch_map

    def get_coil_map(self) -> List[CoilMap]:
        """Return a map of all coils in the machine."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")
        coil_map = []
        for coil in self.machine.coils.values():
            coil_map.append(CoilMap(coil.hw_driver.get_board_name(), coil))

        # sort by board + driver number
        coil_map.sort(key=lambda x: (self._natural_key_sort(x[0]), self._natural_key_sort(str(x[1].hw_driver.number))))
        return coil_map

    def get_light_map(self) -> List[LightMap]:
        """Return a map of all lights in the machine."""
        if not self.is_in_service():
            raise AssertionError("Not in service mode!")
        light_map = []
        for light in self.machine.lights.values():
            light_map.append(LightMap(next(iter(light.hw_drivers.values()))[0].get_board_name(), light))

        # sort by board + driver number
        light_map.sort(key=lambda x: (self._natural_key_sort(x[0]), self._natural_key_sort(str(x[1].config['number']))))
        return light_map
