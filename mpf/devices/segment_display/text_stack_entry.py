from typing import Optional, List

from mpf.core.rgb_color import RGBColor
from mpf.devices.segment_display.transitions import TransitionBase
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType


class TextStackEntry:

    def __init__(self, text: str, color: Optional[List[RGBColor]],
                 flashing: Optional[FlashingType], flash_mask: Optional[str],
                 transition: Optional[TransitionBase], transition_out: Optional[TransitionBase],
                 priority: int = 0, key: str = None):
        self.text = text
        self.colors = color
        self.flashing = flashing
        self.flash_mask = flash_mask
        self.transition = transition
        self.transition_out = transition_out
        self.priority = priority
        self.key = key
