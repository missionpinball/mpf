"""The Color module provides utilities for working with RGB colors.

It is based on the colorutils open-source library:
https://github.com/edaniszewski/colorutils
Copyright (c) 2015 Erick Daniszewski
The MIT License (MIT)
"""
import random

from typing import List, Union, Tuple

from mpf.core.utility_functions import Util

channel_min_val = 0
channel_max_val = 255
rgb_min = (0, 0, 0)
rgb_max = (255, 255, 255)

# Standard web color names and values
named_rgb_colors = dict(
    off=(0, 0, 0),
    aliceblue=(240, 248, 255),
    antiquewhite=(250, 235, 215),
    aqua=(0, 255, 255),
    aquamarine=(127, 255, 212),
    azure=(240, 255, 255),
    beige=(245, 245, 220),
    bisque=(255, 228, 196),
    black=(0, 0, 0),
    blanchedalmond=(255, 235, 205),
    blue=(0, 0, 255),
    blueviolet=(138, 43, 226),
    brown=(165, 42, 42),
    burlywood=(222, 184, 135),
    cadetblue=(95, 158, 160),
    chartreuse=(127, 255, 0),
    chocolate=(210, 105, 30),
    coral=(255, 127, 80),
    cornflowerblue=(100, 149, 237),
    cornsilk=(255, 248, 220),
    crimson=(220, 20, 60),
    cyan=(0, 255, 255),
    darkblue=(0, 0, 139),
    darkcyan=(0, 139, 139),
    darkgoldenrod=(184, 134, 11),
    darkgray=(169, 169, 169),
    darkgreen=(0, 100, 0),
    darkkhaki=(189, 183, 107),
    darkmagenta=(139, 0, 139),
    darkolivegreen=(85, 107, 47),
    darkorange=(255, 140, 0),
    darkorchid=(153, 50, 204),
    darkred=(139, 0, 0),
    darksalmon=(233, 150, 122),
    darkseagreen=(143, 188, 143),
    darkslateblue=(72, 61, 139),
    darkslategray=(47, 79, 79),
    darkturquoise=(0, 206, 209),
    darkviolet=(148, 0, 211),
    deeppink=(255, 20, 147),
    deepskyblue=(0, 191, 255),
    dimgray=(105, 105, 105),
    dodgerblue=(30, 144, 255),
    firebrick=(178, 34, 34),
    floralwhite=(255, 250, 240),
    forestgreen=(34, 139, 34),
    fuchsia=(255, 0, 255),
    gainsboro=(220, 220, 220),
    ghostwhite=(248, 248, 255),
    gold=(255, 215, 0),
    goldenrod=(218, 165, 32),
    gray=(128, 128, 128),
    green=(0, 128, 0),
    greenyellow=(173, 255, 47),
    honeydew=(240, 255, 240),
    hotpink=(255, 105, 180),
    indianred=(205, 92, 92),
    indigo=(75, 0, 130),
    ivory=(255, 255, 240),
    khaki=(240, 230, 140),
    lavender=(230, 230, 250),
    lavenderblush=(255, 240, 245),
    lawngreen=(124, 252, 0),
    lemonchiffon=(255, 250, 205),
    lightblue=(173, 216, 230),
    lightcoral=(240, 128, 128),
    lightcyan=(224, 255, 255),
    lightgoldenrodyellow=(250, 250, 210),
    lightgreen=(144, 238, 144),
    lightgrey=(211, 211, 211),
    lightpink=(255, 182, 193),
    lightsalmon=(255, 160, 122),
    lightseagreen=(32, 178, 170),
    lightskyblue=(135, 206, 250),
    lightslategray=(119, 136, 153),
    lightsteelblue=(176, 196, 222),
    lightyellow=(255, 255, 224),
    lime=(0, 255, 0),
    limegreen=(50, 205, 50),
    linen=(250, 240, 230),
    magenta=(255, 0, 255),
    maroon=(128, 0, 0),
    mediumaquamarine=(102, 205, 170),
    mediumblue=(0, 0, 205),
    mediumorchid=(186, 85, 211),
    mediumpurple=(147, 112, 219),
    mediumseagreen=(60, 179, 113),
    mediumslateblue=(123, 104, 238),
    mediumspringgreen=(0, 250, 154),
    mediumturquoise=(72, 209, 204),
    mediumvioletred=(199, 21, 133),
    midnightblue=(25, 25, 112),
    mintcream=(245, 255, 250),
    mistyrose=(255, 228, 225),
    moccasin=(255, 228, 181),
    navajowhite=(255, 222, 173),
    navy=(0, 0, 128),
    oldlace=(253, 245, 230),
    olive=(128, 128, 0),
    olivedrab=(107, 142, 35),
    orange=(255, 165, 0),
    orangered=(255, 69, 0),
    orchid=(218, 112, 214),
    palegoldenrod=(238, 232, 170),
    palegreen=(152, 251, 152),
    paleturquoise=(175, 238, 238),
    palevioletred=(219, 112, 147),
    papayawhip=(255, 239, 213),
    peachpuff=(255, 218, 185),
    peru=(205, 133, 63),
    pink=(255, 192, 203),
    plum=(221, 160, 221),
    powderblue=(176, 224, 230),
    purple=(128, 0, 128),
    rebeccapurple=(102, 51, 153),
    red=(255, 0, 0),
    rosybrown=(188, 143, 143),
    royalblue=(65, 105, 225),
    saddlebrown=(139, 69, 19),
    salmon=(250, 128, 114),
    sandybrown=(244, 164, 96),
    seagreen=(46, 139, 87),
    seashell=(255, 245, 238),
    sienna=(160, 82, 45),
    silver=(192, 192, 192),
    skyblue=(135, 206, 235),
    slateblue=(106, 90, 205),
    slategray=(112, 128, 144),
    snow=(255, 250, 250),
    springgreen=(0, 255, 127),
    steelblue=(70, 130, 180),
    tan=(210, 180, 140),
    teal=(0, 128, 128),
    thistle=(216, 191, 216),
    tomato=(255, 99, 71),
    turquoise=(64, 224, 208),
    violet=(238, 130, 238),
    wheat=(245, 222, 179),
    white=(255, 255, 255),
    whitesmoke=(245, 245, 245),
    yellow=(255, 255, 0),
    yellowgreen=(154, 205, 50),
)


class RGBColor:

    """One RGB Color."""

    __slots__ = ["_color"]

    def __init__(self, color: Union["RGBColor", str, List[int], Tuple[int, int, int]] = None) -> None:
        """Initialise color."""
        if isinstance(color, RGBColor):
            self._color = color.rgb
        elif isinstance(color, str):
            self._color = RGBColor.string_to_rgb(color)
        elif color:
            self._color = (color[0], color[1], color[2])
        else:
            self._color = rgb_min

    def __eq__(self, other):
        """Return true if equal."""
        return RGBColor(other).rgb == self.rgb

    def __ne__(self, other):
        """Return true if not equal."""
        return not self.__eq__(other)

    def __add__(self, other):
        """Return sum of two RGB colors."""
        if isinstance(other, RGBColor):
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other.rgb
        elif isinstance(other, tuple) and len(other) == 3:
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other
        else:
            raise TypeError(
                "Unsupported operand type(s) for +: '{0}' and '{1}'".format(
                    type(self), type(other)))

        return RGBColor((min(r1 + r2, channel_max_val),
                         min(g1 + g2, channel_max_val),
                         min(b1 + b2, channel_max_val)))

    def __sub__(self, other):
        """Return difference of two RGB colors."""
        if isinstance(other, RGBColor):
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other.rgb
        elif isinstance(other, tuple) and len(other) == 3:
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other
        else:
            raise TypeError(
                "Unsupported operand type(s) for -: '{0}' and '{1}'".format(
                    type(self), type(other)))

        return RGBColor((max(r1 - r2, channel_min_val),
                         max(g1 - g2, channel_min_val),
                         max(b1 - b2, channel_min_val)))

    def __mul__(self, other):
        """Multiple color by scalar."""
        if not isinstance(other, (float, int)):
            raise TypeError(
                "Unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    type(self), type(other)))

        if other < 0:
            raise TypeError("Operand needs to be positive")

        r1, g1, b1 = self.rgb
        return RGBColor((min(int(r1 * other), channel_max_val),
                         min(int(g1 * other), channel_max_val),
                         min(int(b1 * other), channel_max_val)))

    def __iter__(self):
        """Return iterator."""
        return iter(self._color)

    def __str__(self):
        """Return string representation."""
        return "{}".format(self._color)

    def __repr__(self):
        """Return general representation."""
        return "<RGBColor {}>".format(self._color)

    @property
    def red(self):
        """Return the red component of the RGB color representation."""
        return self._color[0]

    @red.setter
    def red(self, value: int):
        self._color = (value, self._color[1], self._color[2])

    @property
    def green(self) -> int:
        """Return the green component of the RGB color representation."""
        return self._color[1]

    @green.setter
    def green(self, value: int):
        self._color = (self._color[0], value, self._color[2])

    @property
    def blue(self) -> int:
        """Return the blue component of the RGB color representation."""
        return self._color[2]

    @blue.setter
    def blue(self, value: int):
        self._color = (self._color[0], self._color[1], value)

    @property
    def rgb(self) -> Tuple[int, int, int]:
        """Return an RGB representation of the color."""
        return self._color

    @rgb.setter
    def rgb(self, value: Tuple[int, int, int]):
        self._color = value

    @property
    def hex(self) -> str:
        """Return a 6-char HEX representation of the color."""
        return RGBColor.rgb_to_hex(self.rgb)

    @hex.setter
    def hex(self, value: str):
        self._color = RGBColor.hex_to_rgb(value)

    @property
    def name(self) -> str:
        """Return the color name or None.

        Returns a string containing a standard color name or None
        if the current RGB color does not have a standard name.
        """
        # pylint: disable-msg=consider-using-dict-comprehension
        return dict(
            [(_v, _k) for _k, _v in list(named_rgb_colors.items())]).get(
            self._color)

    @name.setter
    def name(self, value: str):
        self._color = RGBColor.name_to_rgb(value)

    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert an RGB color representation to a HEX color representation.

        (r, g, b) :: r -> [0, 255]
                     g -> [0, 255]
                     b -> [0, 255]
        :param rgb: A tuple of three numeric values corresponding to the red, green, and blue value.
        :return: HEX representation of the input RGB value.
        :rtype: str
        """
        r, g, b = rgb
        return "{0}{1}{2}".format(hex(int(r))[2:].zfill(2),
                                  hex(int(g))[2:].zfill(2),
                                  hex(int(b))[2:].zfill(2))

    @staticmethod
    def hex_to_rgb(_hex: str, default=None) -> Tuple[int, int, int]:
        """Convert a HEX color representation to an RGB color representation.

        Args:
            _hex: The 3- or 6-char hexadecimal string representing the color
                value.
            default: The default value to return if _hex is invalid.

        Returns: RGB representation of the input HEX value as a 3-item tuple
            with each item being an integer 0-255.

        """
        if not Util.is_hex_string(_hex):
            return default

        _hex = str(_hex).strip('#')

        n = len(_hex) // 3
        r = int(_hex[:n], 16)
        g = int(_hex[n:2 * n], 16)
        b = int(_hex[2 * n:3 * n], 16)
        return r, g, b

    @staticmethod
    def blend(start_color, end_color, fraction):
        """Blend two colors.

        Args:
            start_color: The start color
            end_color:  The end color
            fraction: The fraction between 0 and 1 that is used to set the
                blend point between the two colors.

        Returns: An RGBColor object that is a blend between the start and end
            colors

        """
        if isinstance(start_color, RGBColor):
            start_color = start_color.rgb
        else:
            start_color = RGBColor(start_color).rgb

        if isinstance(end_color, RGBColor):
            end_color = end_color.rgb
        else:
            end_color = RGBColor(start_color).rgb

        output_color = tuple(start_color[i] + int(
            (end_color[i] - start_color[i]) * fraction) for i in range(3))
        return RGBColor(output_color)

    @staticmethod
    def random_rgb() -> Tuple[int, int, int]:
        """Generate a uniformly random RGB value.

        :return: A tuple of three integers with values between 0 and 255 inclusive
        """
        return random.randint(0, 255), random.randint(0, 255), random.randint(
            0, 255)

    @staticmethod
    def name_to_rgb(name: str, default=rgb_min) -> Tuple[int, int, int]:
        """Convert a standard color name to an RGB value (tuple).

        If the name is not found, the default value is returned.
        :param name: A standard color name.
        :param default: The default value to return if the color name is not found.
        :return: RGB representation of the named color.
        :rtype: tuple
        """
        return named_rgb_colors.get(name.lower(), default)

    @staticmethod
    def string_to_rgb(value: str, default=rgb_min) -> Tuple[int, int, int]:
        """Convert a string which could be either a standard color name or a hex value to an RGB value (tuple).

        If the name is not found and the supplied value is not a
        valid hex string it raises an error.
        :param value: A standard color name or hex value.
        :param default: The default value to return if the color name is not found and
        the supplied value is not a valid hex color string.
        :return: RGB representation of the named color.
        :rtype: tuple
        """
        if not value:
            return default

        brightness = None
        if '%' in value:
            value, brightness = value.split("%")

        rgb = named_rgb_colors.get(value)
        if rgb is None:
            # we do not want to call lower every time since this code path is very hot
            # instead we just add the upper case string to the color hash map so next time we will hit the fast path
            rgb = named_rgb_colors.get(value.lower())
            if rgb:
                named_rgb_colors[value] = rgb
        if rgb is None:
            rgb = RGBColor.hex_to_rgb(value)
            if rgb is None:
                raise ColorException("Invalid RGB string: {}".format(value))

        # apply brightness
        if brightness:
            factor = float(int(brightness) / 100)
            rgb = (min(int(rgb[0] * factor), channel_max_val),
                   min(int(rgb[1] * factor), channel_max_val),
                   min(int(rgb[2] * factor), channel_max_val))

        return rgb

    @staticmethod
    def add_color(name: str, color: Union["RGBColor", str, List[int], Tuple[int, int, int]]):
        """Add (or updates if it already exists) a color.

        Note that this is not
        permanent, the list is reset when MPF restarts (though you can define your
        own custom colors in your config file's colors: section). You *can* use
        this function to dynamically change the values of colors in shows (they
        take place the next time an LED switches to that color).

        Args:
            name: String name of the color you want to add/update
            color: The color you want to set. You can pass the same types as
                the RGBColor class constructor, including a tuple or list of
                RGB ints (0-255 each), a hex string, an RGBColor instance, or
                a dictionart of red, green, blue key/value pairs.

        """
        named_rgb_colors[str(name.lower())] = RGBColor(color).rgb


class ColorException(AssertionError):

    """General exception thrown for color utilities non-exit exceptions."""

    pass


class RGBColorCorrectionProfile:

    """Encapsulates a named RGB color correction profile and its associated lookup tables."""

    def __init__(self, name: str = None) -> None:
        """Create a linear correction profile that does not alter color values by default.

        Args:
            name: The color correction profile name

        Returns: None
        """
        self._name = name

        # Default lookup table values (linear)
        self._lookup_table = []             # type: List[List[int]]

        for dummy_channel in range(3):
            self._lookup_table.append([i for i in range(256)])

    def generate_from_parameters(self, gamma=2.5, whitepoint=(1.0, 1.0, 1.0),
                                 linear_slope=1.0, linear_cutoff=0.0):
        """Generate an RGB color correction profile lookup table based on the parameters supplied.

        Args:
            gamma: Exponent for the nonlinear portion of the brightness curve.
            whitepoint: Tuple of (red, green, blue) values to multiply by
                colors prior to gamma correction.
            linear_slope: Slope (output / input) of the linear section of the
                brightness curve.
            linear_cutoff: Y (output) coordinate of intersection between linear
                and nonlinear curves.

        Returns: None
        """
        # Lookup table generation algorithm from the Fadecandy open source
        # server code:
        # https://github.com/scanlime/fadecandy
        # Copyright (c) 2013 Micah Elizabeth Scott
        # The MIT License (MIT)
        scale = 1.0 - linear_cutoff

        for channel in range(3):
            for index in range(256):
                # Scale linear table values by the whitepoint
                value = index / 255.0 * whitepoint[channel]

                if value * linear_slope <= linear_cutoff:
                    value = int(linear_slope * value * 255)
                else:
                    non_linear_input = value - (linear_slope * linear_cutoff)
                    value = int(linear_cutoff + pow(non_linear_input / scale,
                                                    gamma) * scale * 255)

                # Clamp the lookup table value between 0 and 255
                self._lookup_table[channel][index] = max(0, min(value, 255))

    def assign_channel_lookup_table_values(self, channel: int, table_values: List[int]):
        """Assign the specified lookup table values to the profile channel.

        Args:
            channel: The channel number (0..2)
            table_values: A list of 256 integer values between 0 and 255

        """
        if channel not in range(3):
            raise ValueError('Invalid channel number in color correction profile')

        if not isinstance(table_values, list) or len(table_values) != 256:
            raise TypeError('Invalid lookup table values type for color correction profile - '
                            'must be a list of 256 integer values')

        for index in range(256):
            value = table_values[index]
            if not isinstance(value, int) or value < 0 or value > 255:
                raise ValueError('Invalid value in color correction profile channel lookup table - '
                                 'must be integers between 0 and 255')

            self._lookup_table[channel][index] = value

    @property
    def name(self) -> str:
        """Return the color correction profile name.

        Returns:
            str
        """
        return self._name

    def apply(self, color) -> RGBColor:
        """Apply the current color correction profile to the specified RGBColor object.

        Args:
            color: The RGBColor object which to apply the color correction profile.

        Returns: RGBColor
        """
        return RGBColor((self._lookup_table[0][color.red],
                         self._lookup_table[1][color.green],
                         self._lookup_table[2][color.blue]))

    @staticmethod
    def default() -> "RGBColorCorrectionProfile":
        """Create a default profile (gamma-corrected).

        The values for this table come from a web article:
        https://learn.adafruit.com/led-tricks-gamma-correction/the-quick-fix
        """
        default_profile = RGBColorCorrectionProfile('default')

        # Create standard gamma correction lookup table values
        table = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
                 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2,
                 2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5,
                 5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10,
                 10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
                 17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
                 25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
                 37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
                 51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
                 69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
                 90, 92, 93, 95, 96, 98, 99, 101, 102, 104, 105, 107, 109, 110, 112, 114,
                 115, 117, 119, 120, 122, 124, 126, 127, 129, 131, 133, 135, 137, 138, 140, 142,
                 144, 146, 148, 150, 152, 154, 156, 158, 160, 162, 164, 167, 169, 171, 173, 175,
                 177, 180, 182, 184, 186, 189, 191, 193, 196, 198, 200, 203, 205, 208, 210, 213,
                 215, 218, 220, 223, 225, 228, 231, 233, 236, 239, 241, 244, 247, 249, 252, 255]

        # Assign the color correction profile channel lookup table values
        default_profile.assign_channel_lookup_table_values(0, table)
        default_profile.assign_channel_lookup_table_values(1, table)
        default_profile.assign_channel_lookup_table_values(2, table)

        return default_profile
