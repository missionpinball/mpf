"""Segment displays on light drivers."""
import asyncio
import logging
from collections import namedtuple

from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplaySoftwareFlashPlatformInterface

from mpf.core.platform import SegmentDisplayPlatform

SevenSegmentDisplayMap = namedtuple("SevenSegmentDisplayMap", ["a", "b", "c", "d", "e", "f", "g"])


seven_segments_mapping = {
    None: SevenSegmentDisplayMap(0, 0, 0, 0, 0, 0, 0),
    "0": SevenSegmentDisplayMap(1, 1, 1, 1, 1, 1, 0),
    "1": SevenSegmentDisplayMap(0, 1, 1, 0, 0, 0, 0),
    "2": SevenSegmentDisplayMap(1, 1, 0, 1, 1, 0, 1),
    "3": SevenSegmentDisplayMap(1, 1, 1, 1, 0, 0, 1),
    "4": SevenSegmentDisplayMap(0, 1, 1, 0, 0, 1, 1),
    "5": SevenSegmentDisplayMap(1, 0, 1, 1, 0, 1, 1),
    "6": SevenSegmentDisplayMap(1, 0, 1, 1, 1, 1, 1),
    "7": SevenSegmentDisplayMap(1, 1, 1, 0, 0, 0, 0),
    "8": SevenSegmentDisplayMap(1, 1, 1, 1, 1, 1, 1),
    "9": SevenSegmentDisplayMap(1, 1, 1, 1, 0, 1, 1),
    "A": SevenSegmentDisplayMap(1, 1, 1, 0, 1, 1, 1),
    "b": SevenSegmentDisplayMap(0, 0, 1, 1, 1, 1, 1),
    "C": SevenSegmentDisplayMap(1, 0, 0, 1, 1, 1, 0),
    "D": SevenSegmentDisplayMap(0, 1, 1, 1, 1, 0, 1),
    "E": SevenSegmentDisplayMap(1, 0, 0, 1, 1, 1, 1),
    "F": SevenSegmentDisplayMap(1, 0, 0, 0, 1, 1, 1),
}


class LightSegmentDisplay(SegmentDisplaySoftwareFlashPlatformInterface):

    """Segment display which drives lights."""

    __slots__ = ["_lights", "_segment_type", "_key"]

    def __init__(self, number, lights, segment_type):
        """Initialise segment display."""
        super().__init__(number)
        self._lights = lights
        self._segment_type = segment_type
        self._key = "segment_display_{}".format(number)

    def _set_text(self, text: str) -> None:
        """Set text to lights."""
        # get the last chars for the number of chars we have
        text = text[-len(self._lights):]
        # iterate lights and chars
        for char, lights_for_char in zip(text, self._lights):
            try:
                char_map = seven_segments_mapping[char]
            except KeyError:
                # if there is no
                char_map = seven_segments_mapping[None]
            for name, light in lights_for_char.items():
                if getattr(char_map, name):
                    light.on(key=self._key)
                else:
                    light.remove_from_stack_by_key(key=self._key)


class LightSegmentDisplaysPlatform(SegmentDisplayPlatform):

    """Platform which drives segment displays on lights of another platform."""

    __slots__ = ["log"]

    def __init__(self, machine):
        """Initialise platform."""
        super().__init__(machine)
        self.log = logging.getLogger('Light Segment Displays')
        self.log.debug("Configuring Light Segment Displays")

    def configure_segment_display(self, number: str, platform_settings) -> LightSegmentDisplay:
        """Configure light segment display."""
        settings = self.machine.config_validator.validate_config("light_segment_displays", platform_settings)
        return LightSegmentDisplay(number, lights=settings['lights'], segment_type=settings['type'])
