"""RGBA Color."""
from typing import Tuple, Union, List

from mpf.core.rgb_color import RGBColor


class RGBAColor(RGBColor):

    """RGB Color with alpha channel."""

    def __init__(self, color: Union[RGBColor, str, List[int], Tuple[int, int, int], Tuple[int, int, int, int]]):
        """Initialise RGBA color."""
        if isinstance(color, tuple) and len(color) == 4:
            self.opacity = color[3]
            super().__init__((color[0], color[1], color[2]))
        else:
            self.opacity = 255
            super().__init__(color)

    def __iter__(self):
        """Return iterator."""
        return iter([self._color[0], self._color[1], self._color[2], self.opacity])

    def __str__(self):
        """Return string representation."""
        return "{} Opacity: {}".format(self._color, self.opacity)
