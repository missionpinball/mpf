"""Segment displays on light drivers."""
import logging
from mpf.core.segment_mappings import SEVEN_SEGMENTS, BCD_SEGMENTS, FOURTEEN_SEGMENTS, SIXTEEN_SEGMENTS
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplaySoftwareFlashPlatformInterface
from mpf.core.platform import SegmentDisplaySoftwareFlashPlatform


class LightSegmentDisplay(SegmentDisplaySoftwareFlashPlatformInterface):

    """Segment display which drives lights."""

    __slots__ = ["_lights", "_key", "_segment_map"]

    def __init__(self, number, lights, segment_type):
        """Initialise segment display."""
        super().__init__(number)
        self._lights = lights
        if segment_type == "7segment":
            self._segment_map = SEVEN_SEGMENTS
        elif segment_type == "bcd":
            self._segment_map = BCD_SEGMENTS
        elif segment_type == "14segment":
            self._segment_map = FOURTEEN_SEGMENTS
        elif segment_type == "16segment":
            self._segment_map = SIXTEEN_SEGMENTS
        else:
            raise AssertionError("Invalid segment type {}".format(segment_type))

        self._key = "segment_display_{}".format(number)

    def _set_text(self, text: str) -> None:
        """Set text to lights."""
        # get the last chars for the number of chars we have
        text = text[-len(self._lights):]
        text = text.zfill(len(self._lights))
        # iterate lights and chars
        for char, lights_for_char in zip(text, self._lights):
            try:
                char_map = self._segment_map[ord(char)]
            except KeyError:
                # if there is no
                char_map = self._segment_map[None]
            for name, light in lights_for_char.items():
                if getattr(char_map, name):
                    light.on(key=self._key)
                else:
                    light.remove_from_stack_by_key(key=self._key)


class LightSegmentDisplaysPlatform(SegmentDisplaySoftwareFlashPlatform):

    """Platform which drives segment displays on lights of another platform."""

    __slots__ = ["log", "config"]

    def __init__(self, machine):
        """Initialise platform."""
        super().__init__(machine)
        self.log = logging.getLogger('Light Segment Displays')
        self.log.debug("Configuring Light Segment Displays")
        self.config = self.machine.config_validator.validate_config("light_segment_displays",
                                                                    self.machine.config.get("light_segment_displays"))

    async def configure_segment_display(self, number: str, platform_settings) -> LightSegmentDisplay:
        """Configure light segment display."""
        settings = self.machine.config_validator.validate_config("light_segment_displays_device", platform_settings)
        display = LightSegmentDisplay(number, lights=settings['lights'], segment_type=settings['type'])
        self._handle_software_flash(display)
        return display
