"""Segment display on the FAST platform."""

from typing import List

from mpf.core.utility_functions import Util
from mpf.core.rgb_color import RGBColor
from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText

from mpf.platforms.interfaces.segment_display_platform_interface \
    import SegmentDisplayPlatformInterface, FlashingType


class FASTSegmentDisplay(SegmentDisplayPlatformInterface):

    """FAST segment display."""

    __slots__ = ["serial", "hex_id", "next_color", "next_text"]

    def __init__(self, index, communicator):
        """initialize alpha numeric display."""
        super().__init__(index)
        self.serial = communicator
        self.hex_id = Util.int_to_hex_string(index * 7)
        self.next_color = None
        self.next_text = None

    def set_text(self, text: ColoredSegmentDisplayText, flashing: FlashingType, flash_mask: str) -> None:
        """Set digits to display."""
        del flashing
        del flash_mask
        colors = text.get_colors()
        self.next_text = text
        if colors:
            self._set_color(colors)

    def _set_color(self, colors: List[RGBColor]) -> None:
        """Set display color."""
        #self.serial.platform.info_log("Color: {}".format(colors))
        if len(colors) == 1:
            self.next_color = (RGBColor(colors[0]).hex + ',') * 7
        else:
            self.next_color = ','.join([RGBColor(color).hex for color in colors]) + ','
