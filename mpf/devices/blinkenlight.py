"""Contains the Blinkenlight class."""
import asyncio

from operator import itemgetter

from mpf.core.rgb_color import RGBColor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.exceptions.config_file_error import ConfigFileError

MYPY = False
if MYPY:   # pragma: no cover
    from typing import NoReturn     # pylint: disable-msg=cyclic-import,unused-import


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
        self._color_duration = None
        self._cycle_duration = None

    def load_config(self, config: dict):
        """Load config."""
        super().load_config(config)

        self._color_duration = self.config['color_duration']
        self._cycle_duration = self.config['cycle_duration']
        if (self._color_duration is None and self._cycle_duration is None) or \
           (self._color_duration is not None and self._cycle_duration is not None):
            self._blinkenlight_validation_error(
                "Either color_duration or cycle_duration must be specified, but not both.", 1)

    def _blinkenlight_validation_error(self, msg, error_code) -> "NoReturn":  # pragma: no cover
        raise ConfigFileError('"{}" >> {}'.format(self.name, msg), error_code, "blinkenlight", self.name)

    @property
    def num_colors(self):
        """Return the number of colors (excluding "off") for this blinkenlight."""
        return self._num_colors

    @num_colors.setter
    def num_colors(self, newvalue):
        self._num_colors = newvalue
        # if the number of colors is 0, remove us from the light stack
        if self._num_colors == 0:
            self.light.remove_from_stack_by_key(self._blinkenlight_key)

    @property
    def light(self):
        """Return the light this blinkenlight controls."""
        return self.config['light']

    @property
    def num_colors_in_cycle(self):
        """Similar to num_colors, but adds 1 for the "off" color if there is one between cycles."""
        return self.num_colors + (1 if self._off_between_cycles() else 0)

    @property
    def _blinkenlight_key(self):
        # this is the key that's passed to the light as the color's key
        # so that we can remove this blinkenlight's color from the light stack
        # when all the blinkenlight's colors are removed.
        # This prevents the light from staying in the off state if the blinkenlight
        # was on top of the priority list.
        return 'blinkenlight_{}'.format(self.name)

    def add_color(self, color, key, priority):
        """Add a color to the blinkenlight."""
        # check if this key already exists. If it does, replace it with the incoming color/priority
        existing_color_with_key = [x for x in self._colors if x[1] == key]
        if len(existing_color_with_key) == 0:
            self._colors.append((color, key, priority))
            self.num_colors += 1
            self.info_log('Color {} with key {} added'.format(color, key))
            self._restart()
        elif len(existing_color_with_key) == 1:
            # color with this key already exists. Just update it with this new color and priority
            self._remove_color_with_key(key)
            self.add_color(color, key, priority)

    def remove_all_colors(self):
        """Remove all colors from the blinkenlight."""
        self._colors.clear()
        self.num_colors = 0
        self.info_log('All colors removed')
        self._restart()

    def remove_color_with_key(self, key):
        """Remove a color with a given key from the blinkenlight."""
        color = [x for x in self._colors if x[1] == key]
        if len(color) == 1:
            self._colors.remove(color[0])
            self.num_colors -= 1
            self.info_log('Color removed with key {}'.format(key))
            self._restart()

    def _restart(self):
        self.delay.clear()
        self._sort_colors()
        self._perform_step()

    def _sort_colors(self):
        """Sort the blinkenlights colors by their priority."""
        self._colors = sorted(self._colors, key=itemgetter(2), reverse=True)  # priority is item 2 of the tuple

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
