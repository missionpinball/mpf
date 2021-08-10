"""Contains the Blinkenlight class."""
import asyncio
from functools import partial

from typing import Set, Dict, List, Tuple, Any

from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.exceptions.config_file_error import ConfigFileError

@DeviceMonitor("num_colors", "light")
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
        # if the number of colors is 0, remove us from the light stack
        if self._num_colors == 0:
            self.light.remove_from_stack_by_key(self._blinkenlight_key)

    @property
    def light(self):
        return self.config['light']

    @property
    def num_colors_in_cycle(self):
        # similar to num_colors, but adds 1 for the "off" color if there is one between cycles
        return self.num_colors + (1 if self._off_between_cycles() else 0)


    @property
    def _blinkenlight_key(self):
        # this is the key that's passed to the light as the color's key
        # so that we can remove this blinkenlight's color from the light stack
        # when all the blinkenlight's colors are removed.
        # This prevents the light from staying in the off state if the blinkenlight
        # was on top of the priority list.
        return 'blinkenlight_{}'.format(self.name)

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
        self.delay.clear()
        self._perform_step()

    def _off_between_cycles(self):
        return (self.config['off_when_multiple'] and len(self._colors) > 1) or (len(self._colors) == 1)

    def _get_time_between_colors_ms(self):
        if self._cycle_duration:
            delay = self._cycle_duration / self.num_colors_in_cycle
        else:
            delay = self._color_duration
        if delay < 1:
            delay = 1
        return delay

    def _get_total_cycle_ms(self):
        if self._cycle_duration:
            return self._cycle_duration
        return self._color_duration * self.num_colors_in_cycle

    def _get_current_color(self):
        now = self.machine.clock.get_time()
        offset_ms = (now * 1000) % self._get_total_cycle_ms()
        color_i = int(offset_ms / self._get_time_between_colors_ms() + 0.5)
        if color_i >= self.num_colors:
            return RGBColor("off")
        return self._colors[color_i][0]

    def _perform_step(self):
        if len(self._colors) == 0:
            return
        light = self.config['light']
        current_color = self._get_current_color()
        color_duration_ms = self._get_time_between_colors_ms()
        cycle_ms = self._get_total_cycle_ms()
        if current_color is None:
            return
        light.color(current_color, priority=self.config['priority'], key=self._blinkenlight_key)
        delay_ms = color_duration_ms - ((self.machine.clock.get_time() * 1000) % cycle_ms) % color_duration_ms
        self.delay.add(delay_ms, self._perform_step)
