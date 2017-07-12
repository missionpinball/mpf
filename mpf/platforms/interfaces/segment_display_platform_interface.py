"""Support for physical segment displays."""
import abc
from typing import Any


class SegmentDisplayPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a segment display in hardware platforms."""

    def __init__(self, number: Any) -> None:
        """Remember the number."""
        self.number = number

    @abc.abstractmethod
    def set_text(self, text: str) -> None:
        """Set a text to the display."""
        pass
