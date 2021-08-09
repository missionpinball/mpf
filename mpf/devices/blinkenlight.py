"""Contains the Blinkenlight class."""
import asyncio
from functools import partial

from typing import Set, Dict, List, Tuple, Any

from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.exceptions.config_file_error import ConfigFileError

@DeviceMonitor("num_colors", "current_color", "light")
class Blinkenlight(SystemWideDevice):

    """A light that alternates between several different colors."""

    config_section = 'blinkenlights'
    collection = 'blinkenlights'
    class_label = 'blinkenlight'

    def __init__(self, machine, name):
        """Initialise blinkenlight."""
        super().__init__(machine, name)

        self._colors = []
        self.delay = DelayManager(machine)
        self._color_i = 0
        self._num_colors = 0

    def load_config(self, config: dict):
        super().load_config(config)

        self._color_duration = self.config['color_duration']
        self._cycle_duration = self.config['cycle_duration']
        if (self._color_duration is None and self._cycle_duration is None) or (self._color_duration is not None and self._cycle_duration is not None):
            self._blinkenlight_validation_error("Either color_duration or cycle_duration must be specified, but not both.", 1)

    def _blinkenlight_validation_error(self, msg, error_code) -> "NoReturn":  # pragma: no cover
        raise ConfigFileError('"{}" >> {}'.format(self.name, msg), error_code, "blinkenlight", self.name)

    @property
    def num_colors(self):
        # I would prefer this to be a calculated value (i.e., just return len(self._colors)), but then there's no setter involved so things like mpf monitor won't know when this value gets updated.
        return self._num_colors

    @num_colors.setter
    def num_colors(self, newValue):
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

    def add_color(self, color, key):
        # only add this color if the key does not already exist
        if len([x for x in self._colors if x[1] == key]) < 1:
            self._colors.append((color, key))
            self.num_colors += 1
            self.info_log('Color {} with key {} added'.format(color, key))

    def remove_all_colors(self):
        self._colors.clear()
        self.num_colors = 0
        self.info_log('All colors removed')

    def remove_color_with_key(self, key):
        color = [x for x in self._colors if x[1] == key]
        if len(color) == 1:
            self._colors.remove(color[0])
            self.num_colors -= 1
            self.info_log('Color removed with key {}'.format(key))

    def _restart(self):
        self._color_i = 0
        self.delay.clear()
        self.config['light'].color(RGBColor("off"))
        self._perform_step()

    def _off_between_cycles(self):
        return (self.config['off_when_multiple'] and len(self._colors) > 1) or (len(self._colors) == 1)

    def _get_delay_ms(self):
        if self._cycle_duration:
            delay = self._cycle_duration / (self.num_colors + (1 if self._off_between_cycles() else 0))
        else:
            delay = self._color_duration
        if delay < 1:
            delay = 1
        return delay

    def _perform_step(self):
        if len(self._colors) == 0:
            return
        light = self.config['light']
        light_color = None
        if self._color_i >= len(self._colors):
            self._color_i = 0
            if self._off_between_cycles():
                light_color = RGBColor("off")
        if light_color is None:
            light_color = self.current_color
            self._color_i += 1
        light.color(light_color)
        self.delay.add(self._get_delay_ms(), self._perform_step)
