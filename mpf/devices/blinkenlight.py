"""Contains the Blinkenlight class."""
from operator import itemgetter

from mpf.core.rgb_color import RGBColor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor

MYPY = False
if MYPY:   # pragma: no cover
    from typing import NoReturn     # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor("num_colors")
class Blinkenlight(SystemWideDevice):

    """A light that alternates between several different colors."""

    config_section = 'blinkenlights'
    collection = 'blinkenlights'
    class_label = 'blinkenlight'

    def __init__(self, machine, name):
        """initialize blinkenlight."""
        super().__init__(machine, name)

        self._colors = []
        self.delay = DelayManager(machine)
        self._color_duration = None
        self._cycle_duration = None
        self.num_colors = 0
        self._light_key = 'blinkenlight_{}'.format(self.name)     # cache the key as string operations as expensive

    def load_config(self, config: dict):
        """Load config."""
        super().load_config(config)

        self._color_duration = self.config['color_duration']
        self._cycle_duration = self.config['cycle_duration']
        if (self._color_duration is None and self._cycle_duration is None) or \
           (self._color_duration is not None and self._cycle_duration is not None):
            self.raise_config_error("Either color_duration or cycle_duration must be specified, but not both.", 1)

    @property
    def light(self):
        """Return the light this blinkenlight controls."""
        return self.config['light']

    @property
    def num_colors_in_cycle(self):
        """Similar to num_colors, but adds 1 for the "off" color if there is one between cycles."""
        return self.num_colors + (1 if self._off_between_cycles() else 0)

    def add_color(self, color, key, priority):
        """Add a color to the blinkenlight."""
        # check if this key already exists. If it does, replace it with the incoming color/priority
        self._colors = [x for x in self._colors if x[1] != key]
        self._colors.append((color, key, priority))
        self.info_log('Color {} with key {} added'.format(color, key))
        self._update_light()

    def remove_all_colors(self):
        """Remove all colors from the blinkenlight."""
        self._colors.clear()
        self.info_log('All colors removed')
        self._update_light()

    def remove_color_with_key(self, key):
        """Remove a color with a given key from the blinkenlight."""
        old_len = len(self._colors)
        self._colors = [x for x in self._colors if x[1] != key]
        if len(self._colors) != old_len:
            self.info_log('Color removed with key {}'.format(key))
            self._update_light()

    def _update_light(self):
        """Update the underlying light."""
        self.delay.clear()
        self.num_colors = len(self._colors)
        if self._colors:
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
        if self.num_colors == 0:
            self.light.remove_from_stack_by_key(self._light_key)
            return
        current_color = self._get_current_color()
        color_duration_ms = self._get_time_between_colors_ms()
        cycle_ms = self._get_total_cycle_ms()
        self.light.color(current_color, priority=self.config['priority'], key=self._light_key)
        delay_ms = color_duration_ms - ((self.machine.clock.get_time() * 1000) % cycle_ms) % color_duration_ms
        self.delay.add(delay_ms, self._perform_step, name="perform_step")
