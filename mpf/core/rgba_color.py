"""RGBA Color."""
from typing import Tuple, Union, List

from mpf.core.rgb_color import RGBColor


class RGBAColor(RGBColor):

    """RGB Color with alpha channel."""

    __slots__ = ["opacity"]

    def __init__(self, color: Union[RGBColor, str, Tuple[int, int, int], Tuple[int, int, int, int], List[int]]) -> None:
        """initialize RGBA color."""
        if isinstance(color, (tuple, list)) and len(color) == 4:
            self.opacity = color[3]     # type: ignore
            super().__init__((color[0], color[1], color[2]))
        else:
            self.opacity = 255
            super().__init__(color)     # type: ignore

    def __iter__(self):
        """Return iterator."""
        return iter([self._color[0], self._color[1], self._color[2], self.opacity])

    def __str__(self):
        """Return string representation."""
        return "{} Opacity: {}".format(self._color, self.opacity)

    @property
    def rgba(self) -> Tuple[int, int, int, int]:
        """Return an RGB representation of the color."""
        return self._color[0], self._color[1], self._color[2], self.opacity

    @rgba.setter
    def rgba(self, value: Tuple[int, int, int, int]):
        self._color = value[0:3]
        self.opacity = value[3]
