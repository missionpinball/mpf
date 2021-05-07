"""Specialized text support classes for segment displays."""

from collections import namedtuple
from typing import Optional, List

from mpf.core.rgb_color import RGBColor

DisplayCharacter = namedtuple("DisplayCharacter", ["char_code", "dot", "comma", "color"])

DOT_CODE = ord(".")
COMMA_CODE = ord(",")
SPACE_CODE = ord(" ")


class SegmentDisplayText:

    """A list of characters with specialized functions for segment displays. Use for display text effects."""

    __slots__ = ["_text"]

    def __init__(self):
        """Initialize segment display text."""
        self._text = []

    # pylint: disable=too-many-arguments
    @classmethod
    def from_str(cls, text: str, display_size: int, collapse_dots: bool, collapse_commas: bool,
                 colors: Optional[List[RGBColor]] = None) -> "SegmentDisplayText":
        """Create from string."""
        new_obj = SegmentDisplayText()
        char_has_dot = False
        char_has_comma = False

        if colors:
            char_colors = colors[:]
            default_color = colors[0]  # the default color is the color of the first character

            # when fewer colors are supplied than text, extend the last color to the end of the text
            if len(char_colors) < len(text):
                char_colors.extend([colors[-1]] * (len(text) - len(char_colors)))
        else:
            char_colors = [None] * len(text)
            default_color = None

        for char in reversed(text):
            char_code = ord(char)
            if collapse_dots and char_code == DOT_CODE:
                char_has_dot = True
                continue
            if collapse_commas and char_code == COMMA_CODE:
                char_has_comma = True
                continue

            # pylint: disable-msg=protected-access
            new_obj._text.insert(0, DisplayCharacter(char_code, char_has_dot, char_has_comma, char_colors.pop()))
            char_has_dot = False
            char_has_comma = False

        # ensure list is the same size as the segment display (cut off on left or right justify characters)
        # pylint: disable-msg=protected-access
        current_length = len(new_obj._text)
        if current_length > display_size:
            for _ in range(current_length - display_size):
                # pylint: disable-msg=protected-access
                new_obj._text.pop(0)
        elif current_length < display_size:
            for _ in range(display_size - current_length):
                # pylint: disable-msg=protected-access
                new_obj._text.insert(0, DisplayCharacter(SPACE_CODE, False, False, default_color))

        return new_obj

    def convert_to_str(self):
        """Convert back to normal text string."""
        text = ""
        for display_character in self:
            text += chr(display_character.char_code)
            if display_character.dot:
                text += "."
            if display_character.comma:
                text += ","

        return text

    def __len__(self):
        """Return length."""
        return self._text.__len__()

    def __getitem__(self, item):
        """Return item or slice."""
        if isinstance(item, slice):
            items = self._text.__getitem__(item)
            new_list = SegmentDisplayText()
            new_list._text = items
            return new_list

        return self._text.__getitem__(item)

    def extend(self, other_list):
        """Extend list."""
        # pylint: disable-msg=protected-access
        self._text.extend(other_list._text)

    def get_colors(self):
        """Get the list of colors for each character (if set)."""
        # if any colors are set to None, return None
        if any([not display_character.color for display_character in self]):
            return None
        return [display_character.color for display_character in self]
