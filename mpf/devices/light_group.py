"""Light group devices to comfortably configure groups of lights."""
import abc
import copy

import math

from typing import List

from mpf.core.machine import MachineController

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.light import Light


class LightGroup(SystemWideDevice):

    """An abstract group of lights."""

    __slots__ = ["lights"]

    def __init__(self, machine: MachineController, name) -> None:
        """Initialise light group."""
        super().__init__(machine, name)

        self.lights = []        # type: List[Light]

    @classmethod
    def prepare_config(cls, config: dict, is_mode_config: bool):
        """Add light_template and number to config.

        Args:
        ----
            config: unparsed config
            is_mode_config: if in mode (not used)
        """
        del is_mode_config
        if 'light_template' not in config:
            config['light_template'] = {}

        return config

    async def _initialize(self):
        await super()._initialize()
        self._create_lights()

        for light in self.lights:
            await light.device_added_system_wide()

    def get_token(self):
        """Return all lights in group as token."""
        return {'lights': self.lights}

    def _create_light_at_index(self, index, x, y, relative_index):
        light = Light(self.machine, "{}_light_{}".format(self.name, relative_index))
        tags = [self.name]
        tags.extend(self.config['tags'])
        light_config = copy.deepcopy(self.config['light_template'])
        if self.config['start_channel']:
            if relative_index == 0:
                light_config['start_channel'] = self.config['start_channel']
            else:
                light_config['previous'] = "{}_light_{}".format(self.name, relative_index - 1)
        elif self.config['number_template']:
            light_config['number'] = self.config['number_template'].format(index)
        else:
            light_config['number'] = index
        light_config['tags'].append(self.name)
        light_config['x'] = x
        light_config['y'] = y
        light_config = light.validate_and_parse_config(light_config, False)
        light.load_config(light_config)
        self.lights.append(light)
        self.machine.lights[light.name] = light

    @abc.abstractmethod
    def _create_lights(self):
        raise NotImplementedError("Implement")

    def color(self, color, fade_ms=None, priority=0, key=None):
        """Call color on all lights in this group."""
        for light in self.lights:
            light.color(color, fade_ms, priority, key)


class LightStrip(LightGroup):

    """A light stripe."""

    config_section = 'light_stripes'
    collection = 'light_stripes'
    class_label = 'light_stripe'

    __slots__ = []  # type: List[str]

    def _create_lights(self):
        distance = 0
        for index in range(self.config['number_start'], self.config['number_start'] + self.config['count']):
            if self.config['start_x'] is not None:
                x = self.config['start_x'] + math.sin(self.config['direction'] / 180 * math.pi) * distance
                y = self.config['start_y'] + math.cos(self.config['direction'] / 180 * math.pi) * distance
                distance += self.config['distance']
            else:
                x = y = None

            relative_index = index - self.config['number_start']
            self._create_light_at_index(index, x, y, relative_index)


class LightRing(LightGroup):

    """A light ring."""

    config_section = 'light_rings'
    collection = 'light_rings'
    class_label = 'light_ring'

    __slots__ = []  # type: List[str]

    def _create_lights(self):
        angle = self.config['start_angle'] / 180 * math.pi
        for index in range(self.config['number_start'], self.config['number_start'] + self.config['count']):
            if self.config['center_x'] is not None:
                x = self.config['center_x'] + math.sin(angle) * self.config['radius']
                y = self.config['center_y'] + math.cos(angle) * self.config['radius']
                angle += 2 * math.pi / self.config['count']
            else:
                x = y = None

            relative_index = index - self.config['number_start']
            self._create_light_at_index(index, x, y, relative_index)
