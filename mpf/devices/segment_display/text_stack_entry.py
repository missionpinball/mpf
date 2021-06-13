"""Text stack entry support class for segment displays."""
from typing import Optional, List

from mpf.core.rgb_color import RGBColor
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType


# pylint: disable=too-many-instance-attributes,too-many-arguments,too-few-public-methods
class TextStackEntry:

    """An entry in the text stack for a segment display."""

    __slots__ = ["text", "colors", "flashing", "flash_mask", "transition", "transition_out", "priority", "key"]

    def __init__(self, text: str, color: Optional[List[RGBColor]],
                 flashing: Optional[FlashingType] = None, flash_mask: Optional[str] = None,
                 transition: Optional[dict] = None, transition_out: Optional[dict] = None,
                 priority: int = 0, key: str = None):
        """Class initializer."""
        self.text = text
        self.colors = color
        self.flashing = flashing
        self.flash_mask = flash_mask
        self.transition = transition
        self.transition_out = transition_out
        self.priority = priority
        self.key = key

    def __repr__(self):
        """Return str representation."""
        return '<TextStackEntry: {} (priority: {}, key: {} colors: {}) >'.format(
            self.text, self.priority, self.key, self.colors)
