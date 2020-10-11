"""Generic mappings for segment displays.

Those mappings are based on David Madison's awesome mappings: https://github.com/dmadison/LED-Segment-ASCII.
You can use convert_segments.py (based on https://github.com/dmadison/LED-Segment-ASCII/issues/2) to recreate them.

BCD were created by us.
"""
from typing import Dict, Union


class TextToSegmentMapper:

    """Helper to map text to segments."""

    @classmethod
    def map_text_to_segments(cls, text, display_width, segment_mapping, embed_dots=True):
        """Map text to a list of segments.

        Text is aligned to the right.
        Optionally, it can embed dots into segments.
        """
        segments = []
        text_position = 0
        while text_position < len(text):
            char = text[text_position]
            text_position += 1
            mapping = segment_mapping.get(ord(char), segment_mapping[None])
            if embed_dots and not mapping.dp:
                # embed dots is enabled and dot is inactive
                try:
                    next_char = text[text_position]
                except IndexError:
                    next_char = " "
                if next_char == ".":
                    # next char is a dot -> turn dot on
                    mapping = mapping.copy_with_dp_on()
                    text_position += 1
            segments.append(mapping)

        # remove leading segments if mapping is too long
        if display_width < len(segments):
            segments = segments[-display_width:]

        while display_width > len(segments):
            # prepend spaces to pad mapping
            segments.insert(0, segment_mapping.get(ord(" "), segment_mapping[None]))

        return segments


class Segment:

    """Mapping for a segment."""

    __slots__ = ["dp", "char"]

    def __init__(self, dp, char):
        """Initialise segment."""
        self.dp = dp
        self.char = char

    def __repr__(self):
        """Return str representation."""
        return "<" + " ".join(["{}={}".format(attr, getattr(self, attr)) for attr in dir(self) if
                               not attr.startswith("__") and not callable(getattr(self, attr))]) + ">"

    def copy_with_dp_on(self):
        """Return a copy of the segment with dp on."""
        attr = {attr: getattr(self, attr) for attr in dir(self) if not attr.startswith("__") and
                not callable(getattr(self, attr))}
        attr['dp'] = 1
        new_segment = self.__class__(**attr)
        return new_segment

    def __eq__(self, other):
        """Compare to segments."""
        attr_self = {attr: getattr(self, attr) for attr in dir(self) if not attr.startswith("__") and
                     not callable(getattr(self, attr))}
        attr_other = {attr: getattr(other, attr) for attr in dir(other) if not attr.startswith("__") and
                      not callable(getattr(other, attr))}
        return attr_self == attr_other


class BcdSegments(Segment):

    """Mapping for BCD segments with dot."""

    __slots__ = ["x3", "x2", "x1", "x0"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, dp, x3, x2, x1, x0, char):
        """Create segment entry."""
        super().__init__(dp, char)
        self.x0 = x0
        self.x1 = x1
        self.x2 = x2
        self.x3 = x3

    def get_dpx4x3x2x1_encoding(self) -> bytes:
        """Return segment in dpx3x2x1x0 order."""
        return bytes([(self.dp << 7) | (self.x3 << 3) | (self.x2 << 2) | (self.x1 << 1) | self.x0])

    def get_x4x3x2x1_encoding(self) -> bytes:
        """Return segment in x3x2x1x0 order."""
        return bytes([(self.x3 << 3) | (self.x2) << 2 | (self.x1) << 1 | self.x0])


BCD_SEGMENTS = {
    None: BcdSegments(dp=0, x3=0, x2=0, x1=0, x0=0, char="not mappable char"),
    33: BcdSegments(dp=1, x3=0, x2=0, x1=0, x0=1, char="!"),    # 1 with dot

    48: BcdSegments(dp=0, x3=0, x2=0, x1=0, x0=0, char="0"),
    49: BcdSegments(dp=0, x3=0, x2=0, x1=0, x0=1, char="1"),
    50: BcdSegments(dp=0, x3=0, x2=0, x1=1, x0=0, char="2"),
    51: BcdSegments(dp=0, x3=0, x2=0, x1=1, x0=1, char="3"),
    52: BcdSegments(dp=0, x3=0, x2=1, x1=0, x0=0, char="4"),
    53: BcdSegments(dp=0, x3=0, x2=1, x1=0, x0=1, char="5"),
    54: BcdSegments(dp=0, x3=0, x2=1, x1=1, x0=0, char="6"),
    55: BcdSegments(dp=0, x3=0, x2=1, x1=1, x0=1, char="7"),
    56: BcdSegments(dp=0, x3=1, x2=0, x1=0, x0=0, char="8"),
    57: BcdSegments(dp=0, x3=1, x2=0, x1=0, x0=1, char="9"),

    63: BcdSegments(dp=1, x3=0, x2=0, x1=1, x0=0, char="?"),    # 2 with dot

    65: BcdSegments(dp=0, x3=1, x2=0, x1=1, x0=0, char="A"),
    66: BcdSegments(dp=0, x3=1, x2=0, x1=1, x0=1, char="B"),
    67: BcdSegments(dp=0, x3=1, x2=1, x1=0, x0=0, char="C"),
    68: BcdSegments(dp=0, x3=1, x2=1, x1=0, x0=1, char="D"),
    69: BcdSegments(dp=0, x3=1, x2=1, x1=1, x0=0, char="E"),
    70: BcdSegments(dp=0, x3=1, x2=1, x1=1, x0=1, char="F"),

    97: BcdSegments(dp=0, x3=1, x2=0, x1=1, x0=0, char="a"),
    98: BcdSegments(dp=0, x3=1, x2=0, x1=1, x0=1, char="b"),
    99: BcdSegments(dp=0, x3=1, x2=1, x1=0, x0=0, char="c"),
    100: BcdSegments(dp=0, x3=1, x2=1, x1=0, x0=1, char="d"),
    101: BcdSegments(dp=0, x3=1, x2=1, x1=1, x0=0, char="e"),
    102: BcdSegments(dp=0, x3=1, x2=1, x1=1, x0=1, char="f"),
}


class SevenSegments(Segment):

    """Mapping for seven segments.

    See segment order here: https://github.com/dmadison/LED-Segment-ASCII/blob/master/README.md.
    """

    __slots__ = ["g", "f", "e", "d", "c", "b", "a"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, dp, g, f, e, d, c, b, a, char):
        """Create segment entry."""
        super().__init__(dp, char)
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f
        self.g = g

    def get_gfedcba_encoding(self) -> bytes:
        """Return segment in gfedcba order."""
        return bytes([(self.g << 6) | (self.f << 5) | (self.e << 4) | (self.d << 3) | (self.c << 2) | (self.b << 1) |
                      self.a])

    def get_dpgfedcba_encoding(self) -> bytes:
        """Return segment in dp gfedcba order."""
        return bytes([(self.dp << 7) | (self.g << 6) | (self.f << 5) | (self.e << 4) | (self.d << 3) | (self.c << 2) |
                      (self.b << 1) | self.a])

    def get_dpgfeabcd_encoding(self) -> bytes:
        """Return segment in dp gfeabcd order."""
        return bytes([(self.dp << 7) | (self.g << 6) | (self.f << 5) | (self.e << 4) | (self.a << 3) | (self.b << 2) |
                      (self.c << 1) | self.d])


SEVEN_SEGMENTS = {
    None: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="not mappable char"),
    32: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="(space)"),
    33: SevenSegments(dp=1, g=0, f=0, e=0, d=0, c=1, b=1, a=0, char="!"),
    34: SevenSegments(dp=0, g=0, f=1, e=0, d=0, c=0, b=1, a=0, char="\""),
    35: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=1, b=1, a=0, char="#"),
    36: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=0, a=1, char="$"),
    37: SevenSegments(dp=1, g=1, f=0, e=1, d=0, c=0, b=1, a=0, char="%"),
    38: SevenSegments(dp=0, g=1, f=0, e=0, d=0, c=1, b=1, a=0, char="&"),
    39: SevenSegments(dp=0, g=0, f=1, e=0, d=0, c=0, b=0, a=0, char="'"),
    40: SevenSegments(dp=0, g=0, f=1, e=0, d=1, c=0, b=0, a=1, char="("),
    41: SevenSegments(dp=0, g=0, f=0, e=0, d=1, c=0, b=1, a=1, char=")"),
    42: SevenSegments(dp=0, g=0, f=1, e=0, d=0, c=0, b=0, a=1, char="*"),
    43: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=0, b=0, a=0, char="+"),
    44: SevenSegments(dp=0, g=0, f=0, e=1, d=0, c=0, b=0, a=0, char=","),
    45: SevenSegments(dp=0, g=1, f=0, e=0, d=0, c=0, b=0, a=0, char="-"),
    46: SevenSegments(dp=1, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="."),
    47: SevenSegments(dp=0, g=1, f=0, e=1, d=0, c=0, b=1, a=0, char="/"),
    48: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=1, b=1, a=1, char="0"),
    49: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=1, b=1, a=0, char="1"),
    50: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=0, b=1, a=1, char="2"),
    51: SevenSegments(dp=0, g=1, f=0, e=0, d=1, c=1, b=1, a=1, char="3"),
    52: SevenSegments(dp=0, g=1, f=1, e=0, d=0, c=1, b=1, a=0, char="4"),
    53: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=0, a=1, char="5"),
    54: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=1, b=0, a=1, char="6"),
    55: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=1, b=1, a=1, char="7"),
    56: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=1, b=1, a=1, char="8"),
    57: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=1, a=1, char="9"),
    58: SevenSegments(dp=0, g=0, f=0, e=0, d=1, c=0, b=0, a=1, char=":"),
    59: SevenSegments(dp=0, g=0, f=0, e=0, d=1, c=1, b=0, a=1, char=";"),
    60: SevenSegments(dp=0, g=1, f=1, e=0, d=0, c=0, b=0, a=1, char="<"),
    61: SevenSegments(dp=0, g=1, f=0, e=0, d=1, c=0, b=0, a=0, char="="),
    62: SevenSegments(dp=0, g=1, f=0, e=0, d=0, c=0, b=1, a=1, char=">"),
    63: SevenSegments(dp=1, g=1, f=0, e=1, d=0, c=0, b=1, a=1, char="?"),
    64: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=1, b=1, a=1, char="@"),
    65: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=1, a=1, char="A"),
    66: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=1, b=0, a=0, char="B"),
    67: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=0, b=0, a=1, char="C"),
    68: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=1, b=1, a=0, char="D"),
    69: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=0, b=0, a=1, char="E"),
    70: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=0, b=0, a=1, char="F"),
    71: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=1, b=0, a=1, char="G"),
    72: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=1, a=0, char="H"),
    73: SevenSegments(dp=0, g=0, f=1, e=1, d=0, c=0, b=0, a=0, char="I"),
    74: SevenSegments(dp=0, g=0, f=0, e=1, d=1, c=1, b=1, a=0, char="J"),
    75: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=0, a=1, char="K"),
    76: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=0, b=0, a=0, char="L"),
    77: SevenSegments(dp=0, g=0, f=0, e=1, d=0, c=1, b=0, a=1, char="M"),
    78: SevenSegments(dp=0, g=0, f=1, e=1, d=0, c=1, b=1, a=1, char="N"),
    79: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=1, b=1, a=1, char="O"),
    80: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=0, b=1, a=1, char="P"),
    81: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=0, b=1, a=1, char="Q"),
    82: SevenSegments(dp=0, g=0, f=1, e=1, d=0, c=0, b=1, a=1, char="R"),
    83: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=0, a=1, char="S"),
    84: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=0, b=0, a=0, char="T"),
    85: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=1, b=1, a=0, char="U"),
    86: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=1, b=1, a=0, char="V"),
    87: SevenSegments(dp=0, g=0, f=1, e=0, d=1, c=0, b=1, a=0, char="W"),
    88: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=1, a=0, char="X"),
    89: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=1, a=0, char="Y"),
    90: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=0, b=1, a=1, char="Z"),
    91: SevenSegments(dp=0, g=0, f=1, e=1, d=1, c=0, b=0, a=1, char="["),
    92: SevenSegments(dp=0, g=1, f=1, e=0, d=0, c=1, b=0, a=0, char="\""),
    93: SevenSegments(dp=0, g=0, f=0, e=0, d=1, c=1, b=1, a=1, char="]"),
    94: SevenSegments(dp=0, g=0, f=1, e=0, d=0, c=0, b=1, a=1, char="^"),
    95: SevenSegments(dp=0, g=0, f=0, e=0, d=1, c=0, b=0, a=0, char="_"),
    96: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=0, b=1, a=0, char="`"),
    97: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=1, b=1, a=1, char="a"),
    98: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=1, b=0, a=0, char="b"),
    99: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=0, b=0, a=0, char="c"),
    100: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=1, b=1, a=0, char="d"),
    101: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=0, b=1, a=1, char="e"),
    102: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=0, b=0, a=1, char="f"),
    103: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=1, a=1, char="g"),
    104: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=0, a=0, char="h"),
    105: SevenSegments(dp=0, g=0, f=0, e=1, d=0, c=0, b=0, a=0, char="i"),
    106: SevenSegments(dp=0, g=0, f=0, e=0, d=1, c=1, b=0, a=0, char="j"),
    107: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=0, a=1, char="k"),
    108: SevenSegments(dp=0, g=0, f=1, e=1, d=0, c=0, b=0, a=0, char="l"),
    109: SevenSegments(dp=0, g=0, f=0, e=1, d=0, c=1, b=0, a=0, char="m"),
    110: SevenSegments(dp=0, g=1, f=0, e=1, d=0, c=1, b=0, a=0, char="n"),
    111: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=1, b=0, a=0, char="o"),
    112: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=0, b=1, a=1, char="p"),
    113: SevenSegments(dp=0, g=1, f=1, e=0, d=0, c=1, b=1, a=1, char="q"),
    114: SevenSegments(dp=0, g=1, f=0, e=1, d=0, c=0, b=0, a=0, char="r"),
    115: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=0, a=1, char="s"),
    116: SevenSegments(dp=0, g=1, f=1, e=1, d=1, c=0, b=0, a=0, char="t"),
    117: SevenSegments(dp=0, g=0, f=0, e=1, d=1, c=1, b=0, a=0, char="u"),
    118: SevenSegments(dp=0, g=0, f=0, e=1, d=1, c=1, b=0, a=0, char="v"),
    119: SevenSegments(dp=0, g=0, f=0, e=1, d=0, c=1, b=0, a=0, char="w"),
    120: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=1, b=1, a=0, char="x"),
    121: SevenSegments(dp=0, g=1, f=1, e=0, d=1, c=1, b=1, a=0, char="y"),
    122: SevenSegments(dp=0, g=1, f=0, e=1, d=1, c=0, b=1, a=1, char="z"),
    123: SevenSegments(dp=0, g=1, f=0, e=0, d=0, c=1, b=1, a=0, char="{"),
    124: SevenSegments(dp=0, g=0, f=1, e=1, d=0, c=0, b=0, a=0, char="|"),
    125: SevenSegments(dp=0, g=1, f=1, e=1, d=0, c=0, b=0, a=0, char="}"),
    126: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=0, b=0, a=1, char="~"),
    127: SevenSegments(dp=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="(del)"),
}


# pylint: disable-msg=too-many-instance-attributes
class FourteenSegments(Segment):

    """Mapping for fourteen segments.

    See segment order here: https://github.com/dmadison/LED-Segment-ASCII/blob/master/README.md.
    """

    __slots__ = ["l", "m", "n", "k", "j", "h", "g2", "g1", "f", "e", "d", "c", "b", "a"]

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def __init__(self, dp, l, m, n, k, j, h, g2, g1, f, e, d, c, b, a, char):   # noqa E741
        """Create segment entry."""
        super().__init__(dp, char)
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f
        self.g1 = g1
        self.g2 = g2
        self.h = h
        self.j = j
        self.k = k
        self.n = n
        self.m = m
        self.l = l  # noqa: E741

    def get_pinmame_encoding(self) -> bytes:
        """Return segment in pinmame order."""
        return bytes([
            (self.g1 << 6) | (self.f << 5) | (self.e << 4) | (self.d << 3) | (self.c << 2) | (self.b << 1) | self.a,
            (self.dp << 7) | (self.l << 6) | (self.m << 5) | (self.n << 4) | (self.g2 << 3) | (self.k << 2) |
            (self.j << 1) | self.h])

    def get_apc_encoding(self) -> bytes:
        """Return segment in d, c, b, a, e, f, g, comma + j, h, m, k, p, r, dp, n order."""
        return bytes([
            (self.dp << 7) | (self.g1 << 6) | (self.f << 5) | (self.e << 4) | (self.a << 3) | (self.b << 2) |
            (self.c << 1) | self.d,
            (self.l << 7) | (self.dp << 6) | (self.n << 5) | (self.m << 4) | (self.k << 3) | (self.g2 << 2) |
            (self.h << 1) | self.j])


FOURTEEN_SEGMENTS = {
    None: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0,    # noqa: E741
                           char="not mappable char"),
    32: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="(space)"), # noqa: E741
    33: FourteenSegments(dp=1, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=1, b=1, a=0, char="!"),   # noqa: E741
    34: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=1, a=0, char="\""),  # noqa: E741
    35: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=1, g1=1, f=0, e=0, d=1, c=1, b=1, a=0, char="#"),   # noqa: E741
    36: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=1, g1=1, f=1, e=0, d=1, c=1, b=0, a=1, char="$"),   # noqa: E741
    37: FourteenSegments(dp=0, l=1, m=1, n=1, k=1, j=1, h=1, g2=1, g1=1, f=1, e=0, d=0, c=1, b=0, a=0, char="%"),   # noqa: E741
    38: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=1, h=1, g2=0, g1=1, f=0, e=1, d=1, c=0, b=0, a=1, char="&"),   # noqa: E741
    39: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="'"),   # noqa: E741
    40: FourteenSegments(dp=0, l=1, m=0, n=0, k=1, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="("),   # noqa: E741
    41: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=1, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char=")"),   # noqa: E741
    42: FourteenSegments(dp=0, l=1, m=1, n=1, k=1, j=1, h=1, g2=1, g1=1, f=0, e=0, d=0, c=0, b=0, a=0, char="*"),   # noqa: E741
    43: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=1, g1=1, f=0, e=0, d=0, c=0, b=0, a=0, char="+"),   # noqa: E741
    44: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char=","),   # noqa: E741
    45: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=0, e=0, d=0, c=0, b=0, a=0, char="-"),   # noqa: E741
    46: FourteenSegments(dp=1, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="."),   # noqa: E741
    47: FourteenSegments(dp=0, l=0, m=0, n=1, k=1, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="/"),   # noqa: E741
    48: FourteenSegments(dp=0, l=0, m=0, n=1, k=1, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=1, b=1, a=1, char="0"),   # noqa: E741
    49: FourteenSegments(dp=0, l=0, m=0, n=0, k=1, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=1, b=1, a=0, char="1"),   # noqa: E741
    50: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=0, e=1, d=1, c=0, b=1, a=1, char="2"),   # noqa: E741
    51: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=0, f=0, e=0, d=1, c=1, b=1, a=1, char="3"),   # noqa: E741
    52: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=0, d=0, c=1, b=1, a=0, char="4"),   # noqa: E741
    53: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=0, g2=0, g1=1, f=1, e=0, d=1, c=0, b=0, a=1, char="5"),   # noqa: E741
    54: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=1, d=1, c=1, b=0, a=1, char="6"),   # noqa: E741
    55: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=1, b=1, a=1, char="7"),   # noqa: E741
    56: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=1, d=1, c=1, b=1, a=1, char="8"),   # noqa: E741
    57: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=0, d=1, c=1, b=1, a=1, char="9"),   # noqa: E741
    58: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char=":"),   # noqa: E741
    59: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char=";"),   # noqa: E741
    60: FourteenSegments(dp=0, l=1, m=0, n=0, k=1, j=0, h=0, g2=0, g1=1, f=0, e=0, d=0, c=0, b=0, a=0, char="<"),   # noqa: E741
    61: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=0, e=0, d=1, c=0, b=0, a=0, char="="),   # noqa: E741
    62: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=1, g2=1, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char=">"),   # noqa: E741
    63: FourteenSegments(dp=1, l=0, m=1, n=0, k=0, j=0, h=0, g2=1, g1=0, f=0, e=0, d=0, c=0, b=1, a=1, char="?"),   # noqa: E741
    64: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=1, h=0, g2=1, g1=0, f=1, e=1, d=1, c=0, b=1, a=1, char="@"),   # noqa: E741
    65: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=1, d=0, c=1, b=1, a=1, char="A"),   # noqa: E741
    66: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=1, g1=0, f=0, e=0, d=1, c=1, b=1, a=1, char="B"),   # noqa: E741
    67: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=0, b=0, a=1, char="C"),   # noqa: E741
    68: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=1, c=1, b=1, a=1, char="D"),   # noqa: E741
    69: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=1, f=1, e=1, d=1, c=0, b=0, a=1, char="E"),   # noqa: E741
    70: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=1, f=1, e=1, d=0, c=0, b=0, a=1, char="F"),   # noqa: E741
    71: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=0, f=1, e=1, d=1, c=1, b=0, a=1, char="G"),   # noqa: E741
    72: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=1, d=0, c=1, b=1, a=0, char="H"),   # noqa: E741
    73: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=1, c=0, b=0, a=1, char="I"),   # noqa: E741
    74: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=1, d=1, c=1, b=1, a=0, char="J"),   # noqa: E741
    75: FourteenSegments(dp=0, l=1, m=0, n=0, k=1, j=0, h=0, g2=0, g1=1, f=1, e=1, d=0, c=0, b=0, a=0, char="K"),   # noqa: E741
    76: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=0, b=0, a=0, char="L"),   # noqa: E741
    77: FourteenSegments(dp=0, l=0, m=0, n=0, k=1, j=0, h=1, g2=0, g1=0, f=1, e=1, d=0, c=1, b=1, a=0, char="M"),   # noqa: E741
    78: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=1, g2=0, g1=0, f=1, e=1, d=0, c=1, b=1, a=0, char="N"),   # noqa: E741
    79: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=1, b=1, a=1, char="O"),   # noqa: E741
    80: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=1, d=0, c=0, b=1, a=1, char="P"),   # noqa: E741
    81: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=1, b=1, a=1, char="Q"),   # noqa: E741
    82: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=1, d=0, c=0, b=1, a=1, char="R"),   # noqa: E741
    83: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=0, d=1, c=1, b=0, a=1, char="S"),   # noqa: E741
    84: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=1, char="T"),   # noqa: E741
    85: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=1, b=1, a=0, char="U"),   # noqa: E741
    86: FourteenSegments(dp=0, l=0, m=0, n=1, k=1, j=0, h=0, g2=0, g1=0, f=1, e=1, d=0, c=0, b=0, a=0, char="V"),   # noqa: E741
    87: FourteenSegments(dp=0, l=1, m=0, n=1, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=0, c=1, b=1, a=0, char="W"),   # noqa: E741
    88: FourteenSegments(dp=0, l=1, m=0, n=1, k=1, j=0, h=1, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="X"),   # noqa: E741
    89: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=1, e=0, d=1, c=1, b=1, a=0, char="Y"),   # noqa: E741
    90: FourteenSegments(dp=0, l=0, m=0, n=1, k=1, j=0, h=0, g2=0, g1=0, f=0, e=0, d=1, c=0, b=0, a=1, char="Z"),   # noqa: E741
    91: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=1, c=0, b=0, a=1, char="["),   # noqa: E741
    92: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=1, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="\""),  # noqa: E741
    93: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=1, c=1, b=1, a=1, char="]"),   # noqa: E741
    94: FourteenSegments(dp=0, l=1, m=0, n=1, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="^"),   # noqa: E741
    95: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=1, c=0, b=0, a=0, char="_"),   # noqa: E741
    96: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=1, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="`"),   # noqa: E741
    97: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=0, h=0, g2=0, g1=1, f=0, e=1, d=1, c=0, b=0, a=0, char="a"),   # noqa: E741
    98: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=0, g2=0, g1=1, f=1, e=1, d=1, c=0, b=0, a=0, char="b"),   # noqa: E741
    99: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=0, e=1, d=1, c=0, b=0, a=0, char="c"),   # noqa: E741
    100: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=0, g2=1, g1=0, f=0, e=0, d=1, c=1, b=1, a=0, char="d"),  # noqa: E741
    101: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=0, g2=0, g1=1, f=0, e=1, d=1, c=0, b=0, a=0, char="e"),  # noqa: E741
    102: FourteenSegments(dp=0, l=0, m=1, n=0, k=1, j=0, h=0, g2=1, g1=1, f=0, e=0, d=0, c=0, b=0, a=0, char="f"),  # noqa: E741
    103: FourteenSegments(dp=0, l=0, m=0, n=0, k=1, j=0, h=0, g2=1, g1=0, f=0, e=0, d=1, c=1, b=1, a=0, char="g"),  # noqa: E741
    104: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=0, h=0, g2=0, g1=1, f=1, e=1, d=0, c=0, b=0, a=0, char="h"),  # noqa: E741
    105: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="i"),  # noqa: E741
    106: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=1, h=0, g2=0, g1=0, f=0, e=1, d=0, c=0, b=0, a=0, char="j"),  # noqa: E741
    107: FourteenSegments(dp=0, l=1, m=1, n=0, k=1, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="k"),  # noqa: E741
    108: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=1, e=1, d=0, c=0, b=0, a=0, char="l"),  # noqa: E741
    109: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=0, h=0, g2=1, g1=1, f=0, e=1, d=0, c=1, b=0, a=0, char="m"),  # noqa: E741
    110: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=0, h=0, g2=0, g1=1, f=0, e=1, d=0, c=0, b=0, a=0, char="n"),  # noqa: E741
    111: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=1, g1=1, f=0, e=1, d=1, c=1, b=0, a=0, char="o"),  # noqa: E741
    112: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=1, g2=0, g1=1, f=1, e=1, d=0, c=0, b=0, a=0, char="p"),  # noqa: E741
    113: FourteenSegments(dp=0, l=0, m=0, n=0, k=1, j=0, h=0, g2=1, g1=0, f=0, e=0, d=0, c=1, b=1, a=0, char="q"),  # noqa: E741
    114: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=1, f=0, e=1, d=0, c=0, b=0, a=0, char="r"),  # noqa: E741
    115: FourteenSegments(dp=0, l=1, m=0, n=0, k=0, j=0, h=0, g2=1, g1=0, f=0, e=0, d=1, c=0, b=0, a=0, char="s"),  # noqa: E741
    116: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=1, f=1, e=1, d=1, c=0, b=0, a=0, char="t"),  # noqa: E741
    117: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=1, d=1, c=1, b=0, a=0, char="u"),  # noqa: E741
    118: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=0, g2=0, g1=0, f=0, e=1, d=0, c=0, b=0, a=0, char="v"),  # noqa: E741
    119: FourteenSegments(dp=0, l=1, m=0, n=1, k=0, j=0, h=0, g2=0, g1=0, f=0, e=1, d=0, c=1, b=0, a=0, char="w"),  # noqa: E741
    120: FourteenSegments(dp=0, l=1, m=0, n=1, k=1, j=0, h=1, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="x"),  # noqa: E741
    121: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=1, h=0, g2=1, g1=0, f=0, e=0, d=1, c=1, b=1, a=0, char="y"),  # noqa: E741
    122: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=0, g2=0, g1=1, f=0, e=0, d=1, c=0, b=0, a=0, char="z"),  # noqa: E741
    123: FourteenSegments(dp=0, l=0, m=0, n=1, k=0, j=0, h=1, g2=0, g1=1, f=0, e=0, d=1, c=0, b=0, a=1, char="{"),  # noqa: E741
    124: FourteenSegments(dp=0, l=0, m=1, n=0, k=0, j=1, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="|"),  # noqa: E741
    125: FourteenSegments(dp=0, l=1, m=0, n=0, k=1, j=0, h=0, g2=1, g1=0, f=0, e=0, d=1, c=0, b=0, a=1, char="}"),  # noqa: E741
    126: FourteenSegments(dp=0, l=0, m=0, n=1, k=1, j=0, h=0, g2=1, g1=1, f=0, e=0, d=0, c=0, b=0, a=0, char="~"),  # noqa: E741
    127: FourteenSegments(dp=0, l=0, m=0, n=0, k=0, j=0, h=0, g2=0, g1=0, f=0, e=0, d=0, c=0, b=0, a=0, char="(del)"),  # noqa: E741
}


# pylint: disable-msg=too-many-instance-attributes
class SixteenSegments(Segment):

    """Mapping for sixteen segments.

    See segment order here: https://github.com/dmadison/LED-Segment-ASCII/blob/master/README.md.
    """

    __slots__ = ["u", "t", "s", "r", "p", "m", "n", "k", "h", "g", "f", "e", "d", "c", "b", "a"]

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def __init__(self, dp, u, t, s, r, p, m, n, k, h, g, f, e, d, c, b, a, char):
        """Create segment entry."""
        super().__init__(dp, char)
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f
        self.g = g
        self.h = h
        self.k = k
        self.n = n
        self.m = m
        self.p = p
        self.r = r
        self.s = s
        self.t = t
        self.u = u


SIXTEEN_SEGMENTS = {
    None: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                          char="not mappable char"),
    32: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                        char="(space)"),
    33: SixteenSegments(dp=1, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=1, c=1, b=0, a=0, char="!"),
    34: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=1, b=0, a=0,
                        char="\""),
    35: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=1, n=0, m=1, k=0, h=0, g=0, f=1, e=1, d=1, c=1, b=0, a=0, char="#"),
    36: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=1, n=0, m=1, k=0, h=1, g=0, f=1, e=1, d=1, c=0, b=1, a=1, char="$"),
    37: SixteenSegments(dp=0, u=1, t=1, s=1, r=0, p=1, n=1, m=1, k=0, h=1, g=0, f=0, e=1, d=1, c=0, b=0, a=1, char="%"),
    38: SixteenSegments(dp=0, u=1, t=0, s=0, r=1, p=0, n=0, m=1, k=1, h=0, g=1, f=1, e=1, d=0, c=0, b=0, a=1, char="&"),
    39: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="'"),
    40: SixteenSegments(dp=0, u=0, t=0, s=0, r=1, p=0, n=1, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="("),
    41: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=0, m=0, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char=")"),
    42: SixteenSegments(dp=0, u=1, t=1, s=1, r=1, p=1, n=1, m=1, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="*"),
    43: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=1, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="+"),
    44: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char=","),
    45: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="-"),
    46: SixteenSegments(dp=1, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="."),
    47: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=1, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="/"),
    48: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=1, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=1, b=1, a=1, char="0"),
    49: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=1, m=0, k=0, h=0, g=0, f=0, e=0, d=1, c=1, b=0, a=0, char="1"),
    50: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=0, g=1, f=1, e=1, d=0, c=1, b=1, a=1, char="2"),
    51: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=0, g=0, f=1, e=1, d=1, c=1, b=1, a=1, char="3"),
    52: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=0, f=0, e=0, d=1, c=1, b=0, a=0, char="4"),
    53: SixteenSegments(dp=0, u=1, t=0, s=0, r=1, p=0, n=0, m=0, k=0, h=1, g=0, f=1, e=1, d=0, c=0, b=1, a=1, char="5"),
    54: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=0, b=1, a=1, char="6"),
    55: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=1, c=1, b=1, a=1, char="7"),
    56: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=1, b=1, a=1, char="8"),
    57: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=0, f=1, e=1, d=1, c=1, b=1, a=1, char="9"),
    58: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char=":"),
    59: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char=";"),
    60: SixteenSegments(dp=0, u=1, t=0, s=0, r=1, p=0, n=1, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="<"),
    61: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=0, g=0, f=1, e=1, d=0, c=0, b=0, a=0, char="="),
    62: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=1, n=0, m=0, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char=">"),
    63: SixteenSegments(dp=1, u=0, t=0, s=1, r=0, p=1, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=1, b=1, a=1, char="?"),
    64: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=1, n=0, m=1, k=0, h=1, g=1, f=1, e=1, d=0, c=1, b=1, a=1, char="@"),
    65: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=1, c=1, b=1, a=1, char="A"),
    66: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=1, n=0, m=1, k=0, h=0, g=0, f=1, e=1, d=1, c=1, b=1, a=1, char="B"),
    67: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=0, c=0, b=1, a=1, char="C"),
    68: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=1, e=1, d=1, c=1, b=1, a=1, char="D"),
    69: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=0, c=0, b=1, a=1, char="E"),
    70: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=0, b=1, a=1, char="F"),
    71: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=0, b=1, a=1, char="G"),
    72: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=1, c=1, b=0, a=0, char="H"),
    73: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=1, e=1, d=0, c=0, b=1, a=1, char="I"),
    74: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=1, e=1, d=1, c=1, b=0, a=0, char="J"),
    75: SixteenSegments(dp=0, u=1, t=0, s=0, r=1, p=0, n=1, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=0, b=0, a=0, char="K"),
    76: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=0, c=0, b=0, a=0, char="L"),
    77: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=1, m=0, k=1, h=1, g=1, f=0, e=0, d=1, c=1, b=0, a=0, char="M"),
    78: SixteenSegments(dp=0, u=0, t=0, s=0, r=1, p=0, n=0, m=0, k=1, h=1, g=1, f=0, e=0, d=1, c=1, b=0, a=0, char="N"),
    79: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=1, b=1, a=1, char="O"),
    80: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=1, b=1, a=1, char="P"),
    81: SixteenSegments(dp=0, u=0, t=0, s=0, r=1, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=1, b=1, a=1, char="Q"),
    82: SixteenSegments(dp=0, u=1, t=0, s=0, r=1, p=1, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=1, b=1, a=1, char="R"),
    83: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=0, f=1, e=1, d=1, c=0, b=1, a=1, char="S"),
    84: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=1, a=1, char="T"),
    85: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=1, d=1, c=1, b=0, a=0, char="U"),
    86: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=1, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=0, b=0, a=0, char="V"),
    87: SixteenSegments(dp=0, u=0, t=1, s=0, r=1, p=0, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=1, c=1, b=0, a=0, char="W"),
    88: SixteenSegments(dp=0, u=0, t=1, s=0, r=1, p=0, n=1, m=0, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="X"),
    89: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=1, n=0, m=0, k=0, h=1, g=0, f=1, e=1, d=1, c=1, b=0, a=0, char="Y"),
    90: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=1, m=0, k=0, h=0, g=0, f=1, e=1, d=0, c=0, b=1, a=1, char="Z"),
    91: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=1, d=0, c=0, b=1, a=0, char="["),
    92: SixteenSegments(dp=0, u=0, t=0, s=0, r=1, p=0, n=0, m=0, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                        char="\""),
    93: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=1, e=0, d=0, c=0, b=0, a=1, char="]"),
    94: SixteenSegments(dp=0, u=0, t=1, s=0, r=1, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="^"),
    95: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=1, e=1, d=0, c=0, b=0, a=0, char="_"),
    96: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0, char="`"),
    97: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=1, e=1, d=0, c=0, b=0, a=0, char="a"),
    98: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=0, d=0, c=0, b=0, a=0, char="b"),
    99: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=1, e=0, d=0, c=0, b=0, a=0, char="c"),
    100: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=1, n=0, m=0, k=0, h=0, g=0, f=0, e=1, d=1, c=1, b=0, a=0,
                         char="d"),
    101: SixteenSegments(dp=0, u=1, t=1, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=1, e=0, d=0, c=0, b=0, a=0,
                         char="e"),
    102: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=1, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=1, a=0,
                         char="f"),
    103: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=1, g=0, f=1, e=0, d=0, c=0, b=0, a=1,
                         char="g"),
    104: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="h"),
    105: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="i"),
    106: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=1, f=1, e=0, d=0, c=0, b=0, a=0,
                         char="j"),
    107: SixteenSegments(dp=0, u=0, t=0, s=1, r=1, p=0, n=1, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="k"),
    108: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="l"),
    109: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=1, n=0, m=0, k=0, h=0, g=1, f=0, e=0, d=1, c=0, b=0, a=0,
                         char="m"),
    110: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="n"),
    111: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=1, e=0, d=0, c=0, b=0, a=0,
                         char="o"),
    112: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=0, n=0, m=1, k=0, h=1, g=1, f=0, e=0, d=0, c=0, b=0, a=1,
                         char="p"),
    113: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=1, g=0, f=0, e=0, d=0, c=0, b=0, a=1,
                         char="q"),
    114: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="r"),
    115: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=1, g=0, f=1, e=0, d=0, c=0, b=0, a=1,
                         char="s"),
    116: SixteenSegments(dp=0, u=1, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=1, g=1, f=1, e=0, d=0, c=0, b=0, a=0,
                         char="t"),
    117: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=1, e=0, d=0, c=0, b=0, a=0,
                         char="u"),
    118: SixteenSegments(dp=0, u=0, t=1, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=1, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="v"),
    119: SixteenSegments(dp=0, u=0, t=1, s=0, r=1, p=0, n=0, m=0, k=0, h=0, g=1, f=0, e=0, d=1, c=0, b=0, a=0,
                         char="w"),
    120: SixteenSegments(dp=0, u=0, t=1, s=0, r=1, p=0, n=1, m=0, k=1, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="x"),
    121: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=1, n=0, m=1, k=0, h=0, g=0, f=0, e=1, d=1, c=1, b=0, a=0,
                         char="y"),
    122: SixteenSegments(dp=0, u=1, t=1, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=1, e=0, d=0, c=0, b=0, a=0,
                         char="z"),
    123: SixteenSegments(dp=0, u=1, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=1, d=0, c=0, b=1, a=0,
                         char="{"),
    124: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=0, n=0, m=1, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="|"),
    125: SixteenSegments(dp=0, u=0, t=0, s=1, r=0, p=1, n=0, m=1, k=0, h=0, g=0, f=1, e=0, d=0, c=0, b=0, a=1,
                         char="}"),
    126: SixteenSegments(dp=0, u=1, t=1, s=0, r=0, p=1, n=1, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="~"),
    127: SixteenSegments(dp=0, u=0, t=0, s=0, r=0, p=0, n=0, m=0, k=0, h=0, g=0, f=0, e=0, d=0, c=0, b=0, a=0,
                         char="(del)"),
}


class AsciiSegment(Segment):

    """Ascii segment mapping."""

    __slots__ = ["ascii_value"]

    def __init__(self, dp, ascii_value, char):
        """Initialise ascii segment."""
        super().__init__(dp, char)
        self.ascii_value = ascii_value

    def get_ascii_encoding(self):
        """Return ascii encoding."""
        return bytes([self.ascii_value])

    def get_ascii_with_dp_encoding(self):
        """Return ascii encoding with bit 7 for dp."""
        return bytes([self.ascii_value + (128 if self.dp else 0)])


ASCII_SEGMENTS = {
    None: AsciiSegment(dp=0, ascii_value=ord(" "), char=" ")
}   # type: Dict[Union[None, int], AsciiSegment]
for i in range(128):
    ASCII_SEGMENTS[i] = AsciiSegment(dp=0, ascii_value=i, char=chr(i))
