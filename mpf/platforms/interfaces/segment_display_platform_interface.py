"""Support for physical segment displays."""
import abc
from typing import Any, List
from enum import Enum

from mpf.core.rgb_color import RGBColor


class FlashingType(Enum):

    """Determine how a segment display should flash."""

    NO_FLASH = False
    FLASH_ALL = True
    FLASH_MATCH = "match"
    FLASH_MASK = "mask"


class SegmentDisplayPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a segment display in hardware platforms."""

    __slots__ = ["number"]

    def __init__(self, number: Any) -> None:
        """Remember the number."""
        self.number = number

    @abc.abstractmethod
    def set_text(self, text: str, flashing: FlashingType, flash_mask: str, colors: List[RGBColor]) -> None:
        """Set a text to the display.

        This text will be right aligned in case the text is shorter than the display.
        If it is too long it will be cropped on the left.
        """
        raise NotImplementedError


class SegmentDisplaySoftwareFlashPlatformInterface(SegmentDisplayPlatformInterface):

    """SegmentDisplayPlatformInterface with software emulation for flashing."""

    __slots__ = ["_flash_on", "_flashing", "_flash_mask", "_text", "_colors", "_display_state"]

    def __init__(self, number: Any) -> None:
        """Remember the number."""
        super().__init__(number)
        self._flash_on = True
        self._flashing = FlashingType.NO_FLASH      # type: FlashingType
        self._flash_mask = ""
        self._text = ""
        self._display_state = ("", [])
        self._colors = []

    def set_software_flash(self, state):
        """Set software flashing state."""
        self._flash_on = state

        if self._flashing == FlashingType.NO_FLASH:
            return

        # do not flash empty text
        if not self._text:
            return

        if state:
            self._set_text_internal(self._text, self._colors)
        else:
            if self._flashing == FlashingType.FLASH_MATCH:
                # blank the last two chars
                self._set_text_internal(self._text[0:-2] + "  ", self._colors)
            elif self._flashing == FlashingType.FLASH_MASK:
                # use the flash_mask to determine which characters to blank
                self._set_text_internal(
                    "".join(char if mask != "F" else " " for char, mask in zip(self._text, self._flash_mask)),
                    self._colors)
            else:
                self._set_text_internal("", self._colors)

    def _set_text_internal(self, text: str, colors: List[RGBColor]):
        new_state = (text, colors)
        if new_state != self._display_state:
            self._display_state = new_state
            self._set_text(text, colors)

    def set_text(self, text: str, flashing: FlashingType, flash_mask: str, colors: List[RGBColor]) -> None:
        """Set a text to the display."""
        self._text = text
        self._colors = colors
        self._flashing = flashing

        if flashing == FlashingType.NO_FLASH:
            self._flash_on = True
        elif flashing == FlashingType.FLASH_MASK:
            self._flash_mask = flash_mask.rjust(len(text))

        if flashing == FlashingType.NO_FLASH or self._flash_on or not text:
            self._set_text_internal(text, colors)

    @abc.abstractmethod
    def _set_text(self, text: str, colors: List[RGBColor]) -> None:
        """Set a text to the display."""
        raise NotImplementedError
