import random
import re
import math

channel_min_val = 0
channel_max_val = 255
rgb_min = (0, 0, 0)
rgb_max = (255, 255, 255)

# Standard web color names and values
named_rgb_colors = {
    'Off': (0, 0, 0),
    'AliceBlue': (240, 248, 255),
    'AntiqueWhite': (250, 235, 215),
    'Aquamarine': (127, 255, 212),
    'Azure': (240, 255, 255),
    'Beige': (245, 245, 220),
    'Bisque': (255, 228, 196),
    'Black': (0, 0, 0),
    'BlanchedAlmond': (255, 235, 205),
    'Blue': (0, 0, 255),
    'BlueViolet': (138, 43, 226),
    'Brown': (165, 42, 42),
    'BurlyWood': (222, 184, 135),
    'CadetBlue': (95, 158, 160),
    'Chartreuse': (127, 255, 0),
    'Chocolate': (210, 105, 30),
    'Coral': (255, 127, 80),
    'CornflowerBlue': (100, 149, 237),
    'Cornsilk': (255, 248, 220),
    'Crimson': (220, 20, 60),
    'Cyan': (0, 255, 255),
    'DarkBlue': (0, 0, 139),
    'DarkCyan': (0, 139, 139),
    'DarkGoldenrod': (184, 134, 11),
    'DarkGray': (169, 169, 169),
    'DarkGreen': (0, 100, 0),
    'DarkKhaki': (189, 183, 107),
    'DarkMagenta': (139, 0, 139),
    'DarkOliveGreen': (85, 107, 47),
    'DarkOrange': (255, 140, 0),
    'DarkOrchid': (153, 50, 204),
    'DarkRed': (139, 0, 0),
    'DarkSalmon': (233, 150, 122),
    'DarkSeaGreen': (143, 188, 143),
    'DarkSlateBlue': (72, 61, 139),
    'DarkSlateGray': (47, 79, 79),
    'DarkTurquoise': (0, 206, 209),
    'DarkViolet': (148, 0, 211),
    'DeepPink': (255, 20, 147),
    'DeepSkyBlue': (0, 191, 255),
    'DimGray': (105, 105, 105),
    'DodgerBlue': (30, 144, 255),
    'FireBrick': (178, 34, 34),
    'FloralWhite': (255, 250, 240),
    'ForestGreen': (34, 139, 34),
    'Gainsboro': (220, 220, 220),
    'GhostWhite': (248, 248, 255),
    'Gold': (255, 215, 0),
    'Goldenrod': (218, 165, 32),
    'Gray': (128, 128, 128),
    'Green': (0, 128, 0),
    'GreenYellow': (173, 255, 47),
    'Honeydew': (240, 255, 240),
    'HotPink': (255, 105, 180),
    'IndianRed': (205, 92, 92),
    'Indigo': (75, 0, 130),
    'Ivory': (255, 255, 240),
    'Khaki': (240, 230, 140),
    'Lavender': (230, 230, 250),
    'LavenderBlush': (255, 240, 245),
    'LawnGreen': (124, 252, 0),
    'LemonChiffon': (255, 250, 205),
    'LightBlue': (173, 216, 230),
    'LightCoral': (240, 128, 128),
    'LightCyan': (224, 255, 255),
    'LightGoldenrodYellow': (250, 250, 210),
    'LightGreen': (144, 238, 144),
    'LightGrey': (211, 211, 211),
    'LightPink': (255, 182, 193),
    'LightSalmon': (255, 160, 122),
    'LightSeaGreen': (32, 178, 170),
    'LightSkyBlue': (135, 206, 250),
    'LightSlateGray': (119, 136, 153),
    'LightSteelBlue': (176, 196, 222),
    'LightYellow': (255, 255, 224),
    'Lime': (0, 255, 0),
    'LimeGreen': (50, 205, 50),
    'Linen': (250, 240, 230),
    'Magenta': (255, 0, 255),
    'Maroon': (128, 0, 0),
    'MediumAquamarine': (102, 205, 170),
    'MediumBlue': (0, 0, 205),
    'MediumOrchid': (186, 85, 211),
    'MediumPurple': (147, 112, 219),
    'MediumSeaGreen': (60, 179, 113),
    'MediumSlateBlue': (123, 104, 238),
    'MediumSpringGreen': (0, 250, 154),
    'MediumTurquoise': (72, 209, 204),
    'MediumVioletRed': (199, 21, 133),
    'MidnightBlue': (25, 25, 112),
    'MintCream': (245, 255, 250),
    'MistyRose': (255, 228, 225),
    'Moccasin': (255, 228, 181),
    'NavajoWhite': (255, 222, 173),
    'Navy': (0, 0, 128),
    'OldLace': (253, 245, 230),
    'Olive': (128, 128, 0),
    'OliveDrab': (107, 142, 35),
    'Orange': (255, 165, 0),
    'OrangeRed': (255, 69, 0),
    'Orchid': (218, 112, 214),
    'PaleGoldenrod': (238, 232, 170),
    'PaleGreen': (152, 251, 152),
    'PaleTurquoise': (175, 238, 238),
    'PaleVioletRed': (219, 112, 147),
    'PapayaWhip': (255, 239, 213),
    'PeachPuff': (255, 218, 185),
    'Peru': (205, 133, 63),
    'Pink': (255, 192, 203),
    'Plum': (221, 160, 221),
    'PowderBlue': (176, 224, 230),
    'Purple': (128, 0, 128),
    'RebeccaPurple': (102, 51, 153),
    'Red': (255, 0, 0),
    'RosyBrown': (188, 143, 143),
    'RoyalBlue': (65, 105, 225),
    'SaddleBrown': (139, 69, 19),
    'Salmon': (250, 128, 114),
    'SandyBrown': (244, 164, 96),
    'SeaGreen': (46, 139, 87),
    'Seashell': (255, 245, 238),
    'Sienna': (160, 82, 45),
    'Silver': (192, 192, 192),
    'SkyBlue': (135, 206, 235),
    'SlateBlue': (106, 90, 205),
    'SlateGray': (112, 128, 144),
    'Snow': (255, 250, 250),
    'SpringGreen': (0, 255, 127),
    'SteelBlue': (70, 130, 180),
    'Tan': (210, 180, 140),
    'Teal': (0, 128, 128),
    'Thistle': (216, 191, 216),
    'Tomato': (255, 99, 71),
    'Turquoise': (64, 224, 208),
    'Violet': (238, 130, 238),
    'Wheat': (245, 222, 179),
    'White': (255, 255, 255),
    'WhiteSmoke': (245, 245, 245),
    'Yellow': (255, 255, 0),
    'YellowGreen': (154, 205, 50),
}


class RGBColor(object):
    """
    The Color module provides utilities for working with RGB colors.  It is based on the colorutils
    open-source library: https://github.com/edaniszewski/colorutils
    Copyright (c) 2015 Erick Daniszewski
    The MIT License (MIT)
    """
    def __init__(self, color=None, **kwargs):
        """ Initialization """

        if isinstance(color, RGBColor):
            self._color = color._color
        else:
            self._color = color if color else rgb_min

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __eq__(self, other):
        """ Equals """
        if isinstance(other, RGBColor):
            return self.rgb == other.rgb
        return False

    def __ne__(self, other):
        """ Not Equals """
        return not self.__eq__(other)

    def __add__(self, other):
        """ Addition of two RGB colors """
        if isinstance(other, RGBColor):
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other.rgb
        elif isinstance(other, tuple) and len(other) == 3:
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other
        else:
            raise TypeError("Unsupported operand type(s) for +: '{0}' and '{1}'".format(type(self), type(other)))

        return RGBColor((min(r1 + r2, channel_max_val), min(g1 + g2, channel_max_val), min(b1 + b2, channel_max_val)))

    def __sub__(self, other):
        """ Subtraction of two RGB colors """
        if isinstance(other, RGBColor):
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other.rgb
        elif isinstance(other, tuple) and len(other) == 3:
            r1, g1, b1 = self.rgb
            r2, g2, b2 = other
        else:
            raise TypeError("Unsupported operand type(s) for -: '{0}' and '{1}'".format(type(self), type(other)))

        return RGBColor((max(r1 - r2, channel_min_val), max(g1 - g2, channel_min_val), max(b1 - b2, channel_min_val)))

    def __iter__(self):
        """ Iterator """
        return iter(self._color)

    def __str__(self):
        """ String representation """
        return "{}".format(self._color)

    def __repr__(self):
        """ General representation """
        return "<RGBColor {}>".format(self._color)

    @property
    def red(self):
        """ The red component of the RGB color representation. """
        return self._color[0]

    @red.setter
    def red(self, value):
        self._color[0] = value

    @property
    def green(self):
        """ The green component of the RGB color representation. """
        return self._color[1]

    @green.setter
    def green(self, value):
        self._color[1] = value

    @property
    def blue(self):
        """ The blue component of the RGB color representation. """
        return self._color[2]

    @blue.setter
    def blue(self, value):
        self._color[2] = value

    @property
    def rgb(self):
        """ An RGB representation of the color. """
        return self._color

    @rgb.setter
    def rgb(self, value):
        self._color = value

    @property
    def hex(self):
        """ A 6-char HEX representation of the color, with a prepended octothorpe. """
        return RGBColor.rgb_to_hex(self.rgb)

    @hex.setter
    def hex(self, value):
        self._color = RGBColor.hex_to_rgb(value)

    @property
    def name(self):
        """ A string containing a standard color name or None if the current
        RGB color does not have a standard name
        """
        return dict([(_v, _k) for _k, _v in named_rgb_colors.items()]).get(self._color)

    @name.setter
    def name(self, value):
        self._color = RGBColor.name_to_rgb(value)

    @staticmethod
    def rgb_to_hex(rgb):
        """
        Convert an RGB color representation to a HEX color representation.
        (r, g, b) :: r -> [0, 255]
                     g -> [0, 255]
                     b -> [0, 255]
        :param rgb: A tuple of three numeric values corresponding to the red, green, and blue value.
        :return: HEX representation of the input RGB value.
        :rtype: str
        """
        r, g, b = rgb
        return "{0}{1}{2}".format(hex(int(r))[2:].zfill(2), hex(int(g))[2:].zfill(2), hex(int(b))[2:].zfill(2))

    @staticmethod
    def hex_to_rgb(_hex, default=None):
        """
        Convert a HEX color representation to an RGB color representation.
        hex :: hex -> [000000, FFFFFF]
        :param _hex: The 3- or 6-char hexadecimal string representing the color value.
        :param default: The default value to return if _hex is invalid.
        :return: RGB representation of the input HEX value.
        :rtype: tuple
        """
        if re.match("((?:[a-fA-F0-9]{3}){1,2})", _hex) is None:
            return default

        _hex = _hex.strip('#')
        n = len(_hex) // 3
        if len(_hex) == 3:
            r = int(_hex[:n] * 2, 16)
            g = int(_hex[n:2 * n] * 2, 16)
            b = int(_hex[2 * n:3 * n] * 2, 16)
        else:
            r = int(_hex[:n], 16)
            g = int(_hex[n:2 * n], 16)
            b = int(_hex[2 * n:3 * n], 16)
        return r, g, b

    @staticmethod
    def rgb_to_hsv(rgb):
        """
        Convert an RGB color representation to an HSV color representation.
        (r, g, b) :: r -> [0, 255]
                     g -> [0, 255]
                     b -> [0, 255]
        :param rgb: A tuple of three numeric values corresponding to the red, green, and blue value.
        :return: HSV representation of the input RGB value.
        :rtype: tuple
        """
        r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
        _min = min(r, g, b)
        _max = max(r, g, b)
        v = _max
        delta = _max - _min

        if _max == 0:
            return 0, 0, v

        s = delta / _max

        if delta == 0:
            delta = 1

        if r == _max:
            h = 60 * (((g - b) / delta) % 6)

        elif g == _max:
            h = 60 * (((b - r) / delta) + 2)

        else:
            h = 60 * (((r - g) / delta) + 4)

        return round(h, 3), round(s, 3), round(v, 3)

    @staticmethod
    def hsv_to_rgb(hsv):
        """
        Convert an HSV color representation to an RGB color representation.
        (h, s, v) :: h -> [0, 360)
                     s -> [0, 1]
                     v -> [0, 1]
        :param hsv: A tuple of three numeric values corresponding to the hue, saturation, and value.
        :return: RGB representation of the input HSV value.
        :rtype: tuple
        """
        h, s, v = hsv
        c = v * s
        h /= 60
        x = c * (1 - abs((h % 2) - 1))
        m = v - c

        if h < 1:
            res = (c, x, 0)
        elif h < 2:
            res = (x, c, 0)
        elif h < 3:
            res = (0, c, x)
        elif h < 4:
            res = (0, x, c)
        elif h < 5:
            res = (x, 0, c)
        elif h < 6:
            res = (c, 0, x)
        else:
            raise ColorException("Unable to convert from HSV to RGB")

        r, g, b = res
        return round((r + m)*255, 3), round((g + m)*255, 3), round((b + m)*255, 3)

    @staticmethod
    def blend(start_color, end_color, fraction):
        """

        Args:
            start_color: The start color
            end_color:  The end color
            fraction: The fraction between 0 and 1 that is used to set the blend point between the
            two colors.

        Returns: An RGBColor object that is a blend between the start and end colors

        """
        if isinstance(start_color, RGBColor):
            start_color = start_color.rgb

        if isinstance(end_color, RGBColor):
            end_color = end_color.rgb

        output_color = tuple(start_color[i] + int((end_color[i] - start_color[i]) * fraction) for i in range(3))
        return RGBColor(output_color)

    @staticmethod
    def random_rgb():
        """
        Generate a uniformly random RGB value.
        :return: A tuple of three integers with values between 0 and 255 inclusive
        """
        return random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)

    @staticmethod
    def name_to_rgb(name, default=rgb_min):
        """
        Converts a standard color name to an RGB value (tuple). If the name is not found,
        the default value is returned.
        :param name: A standard color name.
        :param default: The default value to return if the color name is not found.
        :return: RGB representation of the named color.
        :rtype: tuple
        """
        return named_rgb_colors.get(name, default)

    @staticmethod
    def string_to_rgb(value, default=rgb_min):
        """
        Converts a string which could be either a standard color name or a hex value to
        an RGB value (tuple). If the name is not found and the supplied value is not a
        valid hex string, the default value is returned.
        :param value: A standard color name or hex value.
        :param default: The default value to return if the color name is not found and
        the supplied value is not a valid hex color string.
        :return: RGB representation of the named color.
        :rtype: tuple
        """
        rgb = named_rgb_colors.get(value)
        if rgb is not None:
            return rgb

        rgb = RGBColor.hex_to_rgb(value)
        if rgb is None:
            rgb = default

        return rgb


class ColorException(Exception):
    """ General exception thrown for color utilities non-exit exceptions. """
    pass


class RGBColorCorrectionProfile(object):

    def __init__(self, name=None):
        self._name = name

        # Default lookup table values (linear)
        self._lookup_table = []

        for channel in range(3):
            self._lookup_table.append([i for i in range(256)])

        pass

    def generate_from_parameters(self, gamma=2.5, whitepoint=(1.0, 1.0, 1.0),
                                 linear_slope=1.0, linear_cutoff=0.0):

        scale = 1.0 - linear_cutoff

        for channel in range(3):
            for index in range(256):
                # Scale linear table values by the whitepoint
                self._lookup_table[channel][index] = index / 255.0 * whitepoint[channel]

                if self._lookup_table[channel][index] * linear_slope <= linear_cutoff:
                    self._lookup_table[channel][index] = int(linear_slope * self._lookup_table[channel][index] * 255)
                else:
                    non_linear_input = self._lookup_table[channel][index] - (linear_slope * linear_cutoff)
                    self._lookup_table[channel][index] = int(linear_cutoff + pow(non_linear_input / scale, gamma) * scale * 255)

    @property
    def name(self):
        return self._name

    def apply(self, color):
        return RGBColor((self._lookup_table[0][color.red],
                         self._lookup_table[1][color.green],
                         self._lookup_table[2][color.blue]))

