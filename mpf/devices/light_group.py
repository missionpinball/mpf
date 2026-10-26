"""Light group devices to comfortably configure groups of lights."""
import asyncio

import abc
import copy

import math

from typing import List

from mpf.core.machine import MachineController

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.light import Light


NEOSEG_8DIGIT_ORDER = [
    95, 90, 93, 82, 85, 89, 86, 91, 88, 87, 81, 92, 83, 84, 94,
    104, 76, 79, 96, 99, 103, 100, 77, 102, 101, 75, 78, 97, 98, 80,
    110, 105, 108, 67, 70, 74, 71, 106, 73, 72, 66, 107, 68, 69, 109,
    119, 61, 64, 111, 114, 118, 115, 62, 117, 116, 60, 63, 112, 113, 65,
    5, 0, 3, 52, 55, 59, 56, 1, 58, 57, 51, 2, 53, 54, 4,
    14, 46, 49, 6, 9, 13, 10, 47, 12, 11, 45, 48, 7, 8, 50,
    20, 15, 18, 37, 40, 44, 41, 16, 43, 42, 36, 17, 38, 39, 19,
    29, 31, 34, 21, 24, 28, 25, 32, 27, 26, 30, 33, 22, 23, 35]

NEOSEG_2DIGIT_ORDER = [
    5, 0, 3, 22, 25, 29, 26, 1, 28, 27, 21, 2, 23, 24, 4,
    14, 16, 19, 6, 9, 13, 10, 17, 12, 11, 15, 18, 7, 8, 20]


class LightGroup(SystemWideDevice):

    """An abstract group of lights."""

    __slots__ = ["lights", "_drivers_loaded", "expected_count"]

    def __init__(self, machine: MachineController, name) -> None:
        """Initialize light group."""
        super().__init__(machine, name)

        self.lights = []        # type: List[Light]
        self._drivers_loaded = asyncio.Future()
        self.expected_count = 0

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
        if 'count' in self.config:
            self.expected_count = self.config['count']

        reorder = self._create_lights()

        for light in self.lights:
            await light.device_added_system_wide()

        if reorder:
            self._reorder_lights()

        self._drivers_loaded.set_result(True)

    def get_token(self):
        """Return all lights in group as token."""
        return {'lights': self.lights}

    def _create_light_at_index(self, index, x, y, relative_index):
        new_name_number = relative_index + self.config['name_start_offset']
        if self.config['zero_pad_digits'] > 0:
            formatted_number = f"{new_name_number:0{self.config['zero_pad_digits']}d}"
        else:
            formatted_number = str(new_name_number)

        base_name = self.name
        if self.config['name_template']:
            base_name = self.config['name_template']

        light = Light(self.machine, "{}_light_{}".format(base_name, formatted_number))
        tags = [base_name]
        tags.extend(self.config['tags'])
        light_config = copy.deepcopy(self.config['light_template'])
        if self.config['start_channel'] or self.config['previous']:
            if relative_index == 0:
                if self.config['start_channel']:
                    light_config['start_channel'] = self.config['start_channel']
                else:
                    light_config['previous'] = self.config['previous'].name
            else:
                light_config['previous'] = "{}_light_{}".format(base_name, relative_index - 1)
        elif self.config['number_template']:
            light_config['number'] = self.config['number_template'].format(index)
        else:
            light_config['number'] = index
        light_config['tags'].append(base_name)
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

    def _swap_grb_rgb_channel_offsets(self, offsets):
        """Swap every first and second out of sets of three (GRB->RGB)."""
        adjustments = {0: 1, 1: -1, 2: 0}
        return [
            x + adjustments[x % 3]
            for x in offsets
        ]

    def _reorder_lights(self):
        if self.config['size'] == '8digit':
            #Magic order for 8 digit NeoSeg displays from CobraPin
            order = NEOSEG_8DIGIT_ORDER

        elif self.config['size'] == '2digit':
            #Magic order for 2 digit NeoSeg displays from CobraPin
            order = NEOSEG_2DIGIT_ORDER

        elif self.config['size'] == '8digit-rg-swapped':
            #Magic order for 8 digit NeoSeg displays from CobraPin when platform numbering uses RGB channel order
            order = self._swap_grb_rgb_channel_offsets(NEOSEG_8DIGIT_ORDER)

        elif self.config['size'] == '2digit-rg-swapped':
            #Magic order for 2 digit NeoSeg displays from CobraPin when platform numbering uses RGB channel order
            order = self._swap_grb_rgb_channel_offsets(NEOSEG_2DIGIT_ORDER)
        else:
            order = range(0, len(self.lights))

        mapped_lights = []
        try:
            for i in order:
                mapped_lights.append(self.lights[i])
            self.lights = mapped_lights
        except IndexError:
            self.error_log("Attempted to use light index %s but source list only had %s items", i, len(self.lights))
            raise

    def wait_for_loaded(self):
        """Return future."""
        return asyncio.shield(self._drivers_loaded)


class LightStrip(LightGroup):

    """A light stripe."""

    config_section = 'light_stripes'
    collection = 'light_stripes'
    class_label = 'light_stripe'

    __slots__ = []  # type: List[str]

    def _create_lights(self):
        distance = 0
        for index in range(self.config['number_start'], self.config['number_start'] + self.expected_count):
            if self.config['start_x'] is not None:
                x = self.config['start_x'] + math.sin(self.config['direction'] / 180 * math.pi) * distance
                y = self.config['start_y'] + math.cos(self.config['direction'] / 180 * math.pi) * distance
                distance += self.config['distance']
            else:
                x = y = None

            relative_index = index - self.config['number_start']
            self._create_light_at_index(index, x, y, relative_index)

        return False


class LightRing(LightGroup):

    """A light ring."""

    config_section = 'light_rings'
    collection = 'light_rings'
    class_label = 'light_ring'

    __slots__ = []  # type: List[str]

    def _create_lights(self):
        angle = self.config['start_angle'] / 180 * math.pi
        for index in range(self.config['number_start'], self.config['number_start'] + self.expected_count):
            if self.config['center_x'] is not None:
                x = self.config['center_x'] + math.sin(angle) * self.config['radius']
                y = self.config['center_y'] + math.cos(angle) * self.config['radius']
                angle += 2 * math.pi / self.expected_count
            else:
                x = y = None

            relative_index = index - self.config['number_start']
            self._create_light_at_index(index, x, y, relative_index)

        return False


class NeoSegDisplay(LightGroup):

    """A NeoSeg Display from CobraPin."""

    config_section = 'neoseg_displays'
    collection = 'neoseg_displays'
    class_label = 'neoseg_display'

    __slots__ = []  # type: List[str]

    def _create_lights(self):
        if self.config['size'] in ('8digit', '8digit-rg-swapped'):
            self.expected_count = 120
        elif self.config['size'] in ('2digit', '2digit-rg-swapped'):
            self.expected_count = 30
        else:
            self.warning_log("NeoSegDisplay %s could not determine number of lights to create.", self.name)
            self.expected_count = 0

        for index in range(self.config['number_start'], self.config['number_start'] + self.expected_count):
            x = y = None
            relative_index = index - self.config['number_start']
            self._create_light_at_index(index, x, y, relative_index)

        return True
