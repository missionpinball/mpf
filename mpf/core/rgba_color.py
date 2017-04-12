"""RGBA Color."""
from typing import Tuple, Union

from mpf.core.rgb_color import RGBColor


class RGBAColor(RGBColor):

    """RGB Color with alpha channel."""

    def __init__(self, color: Union[RGBColor, Tuple[int, int, int, int]]):
        """Initialise RGBA color."""
        if isinstance(color, RGBColor):
            self.opacity = 255
            super().__init__(color)
        else:
            self.opacity = color[3]
            super().__init__((color[0], color[1], color[2]))

    def __iter__(self):
        """Return iterator."""
        return iter([self._color[0], self._color[1], self._color[2], self.opacity])

    def __str__(self):
        """Return string representation."""
        return "{} Opacity: {}".format(self._color, self.opacity)
