"""LED group devices to comfortably configure groups of LEDs."""
import abc
import copy

import math

from mpf.core.machine import MachineController

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.led import Led


class LedGroup(SystemWideDevice):

    """An abstract group of LEDs."""

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Make sure LEDs are initialised.

        Args:
            machine: the machine coontroller
        """
        Led.device_class_init(machine)

    def __init__(self, machine: MachineController, name):
        """Initialise LED group."""
        super().__init__(machine, name)

        self.leds = []

    @classmethod
    def prepare_config(cls, config: dict, is_mode_config: bool):
        """Add led_template and number to config.

        Args:
            config: unparsed config
            is_mode_config: if in mode (not used)

        Returns:
        """
        del is_mode_config
        if 'led_template' not in config:
            config['led_template'] = {}

        if 'number' not in config['led_template']:
            config['led_template']['number'] = 'x'

        return config

    def _initialize(self):
        self._create_leds()

        for led in self.leds:
            led.device_added_system_wide()

    def get_token(self):
        """Return all LEDs in group as token."""
        return {'leds': self.leds}

    def _create_led(self, index, x, y):
        led = Led(self.machine, self.name + "_led_" + str(index))
        tags = [self.name]
        tags.extend(self.config['tags'])
        led_config = copy.deepcopy(self.config['led_template'])
        if self.config['number_template']:
            led_config['number'] = self.config['number_template'].format(index)
        else:
            led_config['number'] = index
        led_config['tags'].append(self.name)
        led_config['debug'] = self.debug
        led_config['x'] = x
        led_config['y'] = y
        led_config = led.validate_and_parse_config(led_config, False)
        led.load_config(led_config)
        self.leds.append(led)
        self.machine.leds[led.name] = led

    @abc.abstractmethod
    def _create_leds(self):
        raise NotImplementedError("Implement")

    # pylint: disable-msg=too-many-arguments
    def color(self, color, fade_ms=None, priority=0, key=None, mode=None):
        """Call color on all leds in this group."""
        for led in self.leds:
            led.color(color, fade_ms, priority, key, mode)


class LedStrip(LedGroup):

    """A LED stripe."""

    config_section = 'led_stripes'
    collection = 'led_stripes'
    class_label = 'led_stripe'

    def _create_leds(self):
        distance = 0
        for index in range(self.config['number_start'], self.config['number_start'] + self.config['count']):
            if self.config['start_x'] is not None:
                x = self.config['start_x'] + math.sin(self.config['direction'] / 180 * math.pi) * distance
                y = self.config['start_y'] + math.cos(self.config['direction'] / 180 * math.pi) * distance
                distance += self.config['distance']
            else:
                x = y = None

            self._create_led(index, x, y)


class LedRing(LedGroup):

    """A LED ring."""

    config_section = 'led_rings'
    collection = 'led_rings'
    class_label = 'led_ring'

    def _create_leds(self):
        angle = self.config['start_angle'] / 180 * math.pi
        for index in range(self.config['number_start'], self.config['number_start'] + self.config['count']):
            if self.config['center_x'] is not None:
                x = self.config['center_x'] + math.sin(angle) * self.config['radius']
                y = self.config['center_y'] + math.cos(angle) * self.config['radius']
                angle += 2 * math.pi / self.config['count']
            else:
                x = y = None

            self._create_led(index, x, y)
