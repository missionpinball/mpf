"""Segment displays on light drivers."""
import logging

from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText
from mpf.core.segment_mappings import SEVEN_SEGMENTS, BCD_SEGMENTS, FOURTEEN_SEGMENTS, SIXTEEN_SEGMENTS,\
    EIGHT_SEGMENTS, TextToSegmentMapper
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplaySoftwareFlashPlatformInterface
from mpf.core.platform import SegmentDisplaySoftwareFlashPlatform


class LightSegmentDisplay(SegmentDisplaySoftwareFlashPlatformInterface):

    """Segment display which drives lights."""

    __slots__ = ["_lights", "_key", "_segment_map", "_current_text"]

    def __init__(self, number, lights, segment_type):
        """initialize segment display."""
        super().__init__(number)
        self._lights = lights
        if segment_type == "7segment":
            self._segment_map = SEVEN_SEGMENTS
        elif segment_type == "bcd":
            self._segment_map = BCD_SEGMENTS
        elif segment_type == "8segment":
            self._segment_map = EIGHT_SEGMENTS
        elif segment_type == "14segment":
            self._segment_map = FOURTEEN_SEGMENTS
        elif segment_type == "16segment":
            self._segment_map = SIXTEEN_SEGMENTS
        else:
            raise AssertionError("Invalid segment type {}".format(segment_type))

        self._key = "segment_display_{}".format(number)
        self._current_text = None

    def _set_text(self, text: ColoredSegmentDisplayText) -> None:
        """Set text to lights."""
        # get the last chars for the number of chars we have
        assert not text.embed_commas
        text = text[-len(self._lights):]
        if text != self._current_text:
            self._current_text = text
            self._update_text()

    def _update_text(self):
        # iterate lights and chars
        mapped_text = TextToSegmentMapper.map_segment_text_to_segments_with_color(
            self._current_text, len(self._lights), self._segment_map)

        for char, lights_for_char in zip(mapped_text, self._lights):
            for name, light in lights_for_char.items():
                if getattr(char[0], name):
                    light.color(color=char[1], key=self._key)
                else:
                    light.remove_from_stack_by_key(key=self._key)


class LightSegmentDisplaysPlatform(SegmentDisplaySoftwareFlashPlatform):

    """Platform which drives segment displays on lights of another platform."""

    __slots__ = ["log", "config"]

    def __init__(self, machine):
        """initialize platform."""
        super().__init__(machine)
        self.log = logging.getLogger('Light Segment Displays')
        self.log.debug("Configuring Light Segment Displays")
        self.config = self.machine.config_validator.validate_config("light_segment_displays",
                                                                    self.machine.config.get("light_segment_displays"))

    @classmethod
    def get_segment_display_config_section(cls):
        """Return addition config section for segment displays."""
        return "light_segment_displays_device"

    async def configure_segment_display(self, number: str, display_size: int, platform_settings) -> LightSegmentDisplay:
        """Configure light segment display."""
        del display_size

        if platform_settings['lights'] != []:
            _lights = platform_settings['lights']
        else:
            #currently supporting 14segment displays
            segments = ['a','b','c','d','e','f','g1','g2','h','j','k','l','m','n','dp']
            digit_len = len(segments)

            #get single list of all lights
            _lights = []
            for lt_group in platform_settings['light_groups']:
                await lt_group.wait_for_loaded()
                _lights.append(lt_group.lights)
                self.log.debug("last light in group %s", lt_group.lights[-1].name)
            _lights = [num for sublist in _lights for num in sublist]

            #split list into dicts of digits
            _lights = [_lights[i:i + digit_len] for i in range(0, len(_lights), digit_len)]
            _lights = [dict(zip(segments,digit_lights)) for digit_lights in _lights]

        display = LightSegmentDisplay(number,
                                      lights=_lights,
                                      segment_type=platform_settings['type'])
        self._handle_software_flash(display)
        return display
