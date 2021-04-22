"""Specialized text support classes for segment displays."""

from collections import namedtuple

DisplayCharacter = namedtuple("DisplayCharacter", ["char_code", "dot", "comma"])


class SegmentDisplayText(list):

    """A list of characters with specialized functions for segment displays. Use for display text effects."""

    DOT_CODE = ord(".")
    COMMA_CODE = ord(",")
    SPACE_CODE = ord(" ")

    def __init__(self, text: str, display_size: int, collapse_dots: bool, collapse_commas: bool) -> None:
        """Class initializer."""
        super().__init__()

        char_has_dot = False
        char_has_comma = False

        for char in reversed(text):
            char_code = ord(char)
            if collapse_dots and char_code == self.DOT_CODE:
                char_has_dot = True
                continue
            if collapse_commas and char_code == self.COMMA_CODE:
                char_has_comma = True
                continue

            self.insert(0, DisplayCharacter(char_code, char_has_dot, char_has_comma))
            char_has_dot = False
            char_has_comma = False

        # ensure list is the same size as the segment display (cut off on left or right justify characters)
        current_length = len(self)
        if current_length > display_size:
            for _ in range(current_length - display_size):
                self.pop(0)
        elif current_length < display_size:
            for _ in range(display_size - current_length):
                self.insert(0, DisplayCharacter(self.SPACE_CODE, False, False))

    @staticmethod
    def convert_to_str(display_character_list: list):
        """Convert back to normal text string."""
        text = ""
        for display_character in display_character_list:
            text += chr(display_character.char_code)
            if display_character.dot:
                text += "."
            if display_character.comma:
                text += ","

        return text
