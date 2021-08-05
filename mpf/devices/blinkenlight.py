"""Contains the Blinkenlight class."""
import asyncio
from functools import partial

from typing import Set, Dict, List, Tuple, Any

from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.delays import DelayManager

class Blinkenlight(SystemWideDevice):

    """A light that alternates between several different colors."""

    config_section = 'blinkenlights'
    collection = 'blinkenlights'
    class_label = 'blinkenlight'

    def __init__(self, machine, name):
        """Initialise blinkenlight."""
        super().__init__(machine, name)

        # self.each_duration = 0
        # self.off_duration = 0
        # self.off_when_multiple = False
        # self.light = None   # type: Light
        self._colors = []
        self.delay = DelayManager(machine)
        self._current_color = 0

    @property
    def colors(self):
        return self._colors

    # @colors.setter
    # def colors(self, newValue):
    #     if not isinstance(newValue, tuple):
    #         return
    #     if len(newValue) != 2:
    #         return
    #     self._colors.append(newValue)
    #     self._restart()
        
    def _restart(self):
        self._current_color = 0
        self.delay.clear()
        self.config['light'].color(RGBColor("off"))
        self._perform_step()

    def _perform_step(self):
        if len(self._colors) == 0:
            return
        light = self.config['light']
        if self._current_color >= len(self._colors):
            self._current_color = 0
            if (self.config['off_when_multiple'] and len(self._colors) > 1) or (len(self._colors) == 1):
                light.color(RGBColor("off"))
                self.delay.add(self.config['off_duration'] * 1000, self._perform_step)
                return
        light.color(self._colors[self._current_color][0])
        self.delay.add(self.config['each_duration'] * 1000, self._perform_step)
        self._current_color += 1
