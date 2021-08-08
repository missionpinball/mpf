"""Contains the Blinkenlight class."""
import asyncio
from functools import partial

from typing import Set, Dict, List, Tuple, Any

from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor

@DeviceMonitor("num_colors", "current_color", "light")
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
        self._color_i = 0
        self._num_colors = 0
        # Add this device to the blinkenlight section
        self.machine.blinkenlights[name] = self

    @property
    def colors(self):
        return self._colors

    @property
    def num_colors(self):
        # self.info_log('num_colors queried - returning {}'.format(len(self._colors)))
        return len(self._colors)

    @num_colors.setter
    def num_colors(self, newValue):
        # self.info_log('num_colors set')
        self._num_colors = newValue

    @property
    def current_color(self):
        if self._color_i >= len(self._colors):
            return None
        if self._color_i < 0:
            return None
        return self._colors[self._color_i][0]

    @property
    def light(self):
        return self.config['light']

    def _restart(self):
        self._color_i = 0
        self.delay.clear()
        self.config['light'].color(RGBColor("off"))
        self._perform_step()

    def _perform_step(self):
        if len(self._colors) == 0:
            return
        light = self.config['light']
        if self._color_i >= len(self._colors):
            self._color_i = 0
            if (self.config['off_when_multiple'] and len(self._colors) > 1) or (len(self._colors) == 1):
                light.color(RGBColor("off"))
                self.delay.add(self.config['off_duration'] * 1000, self._perform_step)
                return
        light.color(self.current_color)
        self.delay.add(self.config['each_duration'] * 1000, self._perform_step)
        self._color_i += 1
