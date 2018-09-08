"""Support for physical segment displays."""
import abc
import asyncio
from typing import Any


class SegmentDisplayPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a segment display in hardware platforms."""

    __slots__ = ["number"]

    def __init__(self, number: Any) -> None:
        """Remember the number."""
        self.number = number

    @abc.abstractmethod
    def set_text(self, text: str, flashing: bool) -> None:
        """Set a text to the display.

        This text will be right aligned in case the text is shorter than the display.
        If it is too long it will be cropped on the left.
        """
        raise NotImplementedError


class SegmentDisplaySoftwareFlashPlatformInterface(SegmentDisplayPlatformInterface):

    """SegmentDisplayPlatformInterface with software emulation for flashing."""

    __slots__ = ["_flash_on", "_flashing", "_text"]

    def __init__(self, number: Any) -> None:
        """Remember the number."""
        super().__init__(number)
        self._flash_on = True
        self._flashing = False
        self._text = ""

    @staticmethod
    def _display_flash_task_done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def set_software_flash(self, state):
        """Set software flashing state."""
        self._flash_on = state

        if not self._flashing:
            return

        # do not flash empty text
        if not self._text:
            return

        if state:
            self._set_text(self._text)
        else:
            self._set_text("")

    def set_text(self, text: str, flashing: bool) -> None:
        """Set a text to the display."""
        self._text = text
        self._flashing = flashing
        if not self._flashing:
            self._flash_on = True
        if not flashing or self._flash_on or not text:
            self._set_text(text)

    @abc.abstractmethod
    def _set_text(self, text: str) -> None:
        """Set a text to the display."""
        raise NotImplementedError
