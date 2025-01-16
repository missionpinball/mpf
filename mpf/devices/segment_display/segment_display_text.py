"""Specialized text support classes for segment displays."""
import abc
from collections import namedtuple
from typing import Optional, List, Union

from mpf.core.rgb_color import RGBColor

DisplayCharacter = namedtuple("DisplayCharacter", ["char_code", "dot", "comma", "color"])

DOT_CODE = ord(".")
COMMA_CODE = ord(",")
SPACE_CODE = ord(" ")


class SegmentDisplayText(metaclass=abc.ABCMeta):

    """A list of characters with specialized functions for segment displays. Use for display text effects."""

    __slots__ = ["_text", "embed_dots", "embed_commas", "use_dots_for_commas"]

    def __init__(self, char_list, embed_dots, embed_commas, use_dots_for_commas):
        """Initialize segment display text."""
        self.embed_dots = embed_dots
        self.embed_commas = embed_commas
        self.use_dots_for_commas = use_dots_for_commas
        self._text = char_list

    # pylint: disable=too-many-arguments
    @classmethod
    def from_str_with_color(cls, text: str, display_size: int, collapse_dots: bool, collapse_commas: bool,
                            use_dots_for_commas: bool, colors: List[RGBColor]) -> "ColoredSegmentDisplayText":
        """Create colored text."""
        return ColoredSegmentDisplayText(
            cls._create_characters(text, display_size, collapse_dots, collapse_commas, use_dots_for_commas, colors[:]),
            collapse_dots, collapse_commas, use_dots_for_commas)

    # pylint: disable=too-many-arguments
    @classmethod
    def from_str(cls, text: str, display_size: int, collapse_dots: bool, collapse_commas: bool,
                 use_dots_for_commas: bool, colors: Optional[List[RGBColor]] = None) -> \
            Union["ColoredSegmentDisplayText", "UncoloredSegmentDisplayText"]:
        """Create from string."""
        if colors:
            return cls.from_str_with_color(text, display_size, collapse_dots, collapse_commas,
                                           use_dots_for_commas, colors[:])

        char_colors = [None] * len(text)
        return UncoloredSegmentDisplayText(
            cls._create_characters(text, display_size, collapse_dots, collapse_commas, use_dots_for_commas,
                                   char_colors), collapse_dots, collapse_commas, use_dots_for_commas)

    @classmethod
    def _embed_dots_and_commas(cls, text: str, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool):
        """Return text with embedded dots and commas."""
        char_has_dot = False
        char_has_comma = False
        char_list = []
        for char in reversed(text):
            char_code = ord(char)
            if collapse_dots and char_code == DOT_CODE or use_dots_for_commas and char_code == COMMA_CODE:
                char_has_dot = True
                continue
            if collapse_commas and char_code == COMMA_CODE:
                char_has_comma = True
                continue
            char_list.insert(0, (char_code, char_has_dot, char_has_comma))
            char_has_dot = False
            char_has_comma = False

        return char_list

    # pylint: disable-msg=too-many-locals
    @classmethod
    def _create_characters(cls, text: str, display_size: int, collapse_dots: bool, collapse_commas: bool,
                           use_dots_for_commas: bool, colors: List[Optional[RGBColor]]) -> List[DisplayCharacter]:
        """Create characters from text and color them.
        - Dots and commas are embedded on the fly.
        - Text will be right aligned on the display, if text is shorter than display spaces add on the left
        - If list of colors is less than the display size then all white will be used,
        - If only one color is given that will be used for the full display
        """
        char_list = []
        uncolored_chars = cls._embed_dots_and_commas(text, collapse_dots, collapse_commas, use_dots_for_commas)

        # Adjust the color array if needed
        if (len(colors)) == 1:
            colors = colors * display_size
        elif len(colors) != display_size:
            #TODO: Log that colors were adjusted to white as default
            colors = [RGBColor("white")] * display_size

        # ensure list is the same size as the segment display
        # cut off on left if too long or right justify characters if too short
        current_length = len(uncolored_chars)
        if current_length > display_size:
            for _ in range(current_length - display_size):
                uncolored_chars.pop(0) #  remove very left char of array if too long
        elif current_length < display_size:
            for _ in range(display_size - current_length):
                uncolored_chars.insert(0, (SPACE_CODE, False, False))

        for i, char in enumerate(uncolored_chars):
            color = colors[i]
            #0: char code 1: char_has_dot 2: char_has_comma
            char_list.append(DisplayCharacter(char[0], char[1], char[2], color))

        return char_list

    def blank_segments(self, flash_mask) -> "SegmentDisplayText":
        """Return new SegmentDisplayText with chars blanked."""
        return ColoredSegmentDisplayText(
            [char if mask != "F" else DisplayCharacter(SPACE_CODE, False, False, char.color)
             for char, mask in zip(self._text, flash_mask)],
            self.embed_dots, self.embed_commas, self.use_dots_for_commas
        )

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
            return self.__class__(self._text.__getitem__(item), self.embed_dots, self.embed_commas,
                                  self.use_dots_for_commas)

        return self._text.__getitem__(item)

    def __eq__(self, other):
        """Return true if two texts and colors are the same."""
        # pylint: disable-msg=protected-access
        return isinstance(other, SegmentDisplayText) and self._text == other._text

    def extend(self, other_list):
        """Extend list."""
        # pylint: disable-msg=protected-access
        self._text.extend(other_list._text)

    @abc.abstractmethod
    def get_colors(self) -> Optional[List[RGBColor]]:
        """Get the list of colors for each character (if set)."""
        raise NotImplementedError()

    def __repr__(self):
        """Return string representation."""
        return "<{} {}>".format(self.__class__, self._text)


class UncoloredSegmentDisplayText(SegmentDisplayText):

    """Segment text without colors."""

    def get_colors(self) -> None:
        """Return None as we are transparent."""
        return None


class ColoredSegmentDisplayText(SegmentDisplayText):

    """Segment text with colors."""

    def get_colors(self) -> List[RGBColor]:
        """Get the list of colors for each character (if set)."""
        return [display_character.color for display_character in self]
