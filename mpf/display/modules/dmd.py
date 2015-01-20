"""Contains the parent class for the DMD MPFDisplay module as well as some
module-level functions related to using DMD files."""
# dmd.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import os
import struct
import pygame  # todo make it so this doesn't crash if pygame is not available
import logging

from mpf.system.display import MPFDisplay


def load_dmd_file(file_name, palette=None, alpha_color=None,
                  alpha_pixels=False):
    """Loads a .DMD file from disk and returns a Pygame surface compatible with
    MPF's DMD display system.

    Args:
        file_name: A string of the file name (with path) of the file to load.
        palette: Optional Python list in the Pygame palette format.
        alpha_color: Whether one of the colors of this rendered DMD should be
            transparent. Default is None, which means this DMD file will have
            no transparencies.
        alpha_pixels. Boolean which controls whether this DMD file should be
            created with pixel-level alpha channels. Default is False.

    Returns: A list of Pygame surfaces. Single-frame DMD files (i.e. static
        images) result in a single-element list. Multi-frame DMD files (i.e.
        animations) result in one list element with a Pygame surface for each
        frame.

    This .DMD format is open source DMD file format originally created for
    Pyprocgame by Gerry Stellenberg and Adam Preble. Support for it in MPF is
    included with permission.

    Details of the file format are here:
    # http://pyprocgame.pindev.org/ref/dmd.html?highlight=dmd#dmd-format
    """

    surface_list = list()
    width = 0
    height = 0
    frame_count = 0

    # This code to read DMD files is based on the following:
    # https://github.com/preble/pyprocgame/blob/master/procgame/dmd/animation.py#L267-L280

    with open(file_name, 'rb') as f:
        f.seek(0, os.SEEK_END)  # Go to the end of the file to get its length
        file_length = f.tell()
        f.seek(4)  # Skip over the 4 byte DMD header.

        frame_count = struct.unpack("I", f.read(4))[0]
        width = struct.unpack("I", f.read(4))[0]
        height = struct.unpack("I", f.read(4))[0]

        if file_length != 16 + width * height * frame_count:
            print "File size inconsistent with header information."

        for frame_index in range(frame_count):
            frame_string = f.read(width * height)

            surface = pygame.image.fromstring(frame_string,
                                              (width, height), 'P')

            if palette:
                surface.set_palette(palette)

            if alpha_color is not None:
                surface.set_colorkey((alpha_color, 0, 0))

            surface_list.append(surface)

    return surface_list


def surface_to_dmd(surface, shades=16, alpha_color=None,
                   weights=(.299, .587, .114)):
    """Converts a 24-bit RGB Pygame surface to surface that's compatible with
    DMD displays in MPF.

    Args:
        surface: The 24-bit Pygame surface you're converting
        shades: How many shades (brightness levels) you want in the new DMD
            surface. Default is 16.
        alpha_color: The pixel value that should be used as an alpha value. (In
            other words, pixels of this color will be transparent.) Default is
            None.
        weights: A tuple of the relative weights of the R, G, and B channels
            that will be used to convert the 24-bit surface to the new surface.
            Default is (.299, .587, .114)

    Returns: An 8-bit Pygame surface ready to display on the DMD.

    DMDs in pinball machines are single color with (usually) 16 different
    shades. So essentially what this method does is convert a 24-bit surface
    with millions of colors to a grayscale surface with 16 shades of gray.
    Since humans perceive different hues to be different intensities, this
    forumula uses relative weights to ensure that the conversion is as accurate
    as possible.

    More information on this conversion process, and the reason we chose the
    default weights we did, is here:
    http://en.wikipedia.org/wiki/Grayscale#Luma_coding_in_video_systems
    """

    width, height = surface.get_size()
    pa = pygame.PixelArray(surface)
    new_surface = pygame.Surface((width, height), depth=8)

    # todo add support for alpha channel (per pixel), and specifying the
    # alpha color before the conversion versus after

    palette = [
        (0, 0, 0),
        (1, 0, 0),
        (2, 0, 0),
        (3, 0, 0),
        (4, 0, 0),
        (5, 0, 0),
        (6, 0, 0),
        (7, 0, 0),
        (8, 0, 0),
        (9, 0, 0),
        (10, 0, 0),
        (11, 0, 0),
        (12, 0, 0),
        (13, 0, 0),
        (14, 0, 0),
        (15, 0, 0)] * 16

    new_surface.set_palette(palette)

    if alpha_color is not None:
        new_surface.set_colorkey((alpha_color, 0, 0))

    new_pa = pygame.PixelArray(new_surface)

    for x in range(width):
        for y in range(height):
            pixel_color = surface.unmap_rgb(pa[x, y])
            pixel_weight = ((pixel_color[0] * weights[0]) +
                            (pixel_color[1] * weights[1]) +
                            (pixel_color[2] * weights[2])) / 255.0

            new_pa[x, y] = int(round(pixel_weight * (shades - 1)))

    return new_pa.surface


def create_palette(bright_color=(255, 0, 0), dark_color=(0, 0, 0),
                   steps=16):
    """Creates a Pygame palette based on the colors passed to it. This method
    is typically used to generate the "on screen" color representations for a
    DMD.

    Args:
        bright_color: A list or tuple of three integers (0-255 each) which
            represents the RGB values of a fully bright (full "on") color of a
            pixel. Default is (255, 0, 0) (red).
        dark_color: A list or tuple of three integers (0-255 each) which
            represents the RGB values of the dark (or "off") color of a pixel.
            Default is (0, 0, 0) (black).
        steps: An integer which is the number of steps (or shades) in the
            palette. Typical values are 2 (1-bit color), 4 (2-bit color), or 16
            (4-bit color). Default is 16.

    Returns: A Pygame palette which is a list of three-item lists. The first
        item will always be the dark_color, and the last item will always
        be the bright_color. The values in between are the steps.
        """

    palette = []
    step_size = [(bright_color[0] - dark_color[0]) / (steps - 1.0),
                 (bright_color[1] - dark_color[1]) / (steps - 1.0),
                 (bright_color[2] - dark_color[2]) / (steps - 1.0)
                 ]

    current_color = dark_color

    # manually add the first entry to ensure it's exactly as entered
    palette.append((int(current_color[0]),
                    int(current_color[1]),
                    int(current_color[2])))

    # calculate all the middle values (all except the dark and bright)
    for i in range(steps-2):
        current_color[0] += step_size[0]
        current_color[1] += step_size[1]
        current_color[2] += step_size[2]
        palette.append((int(current_color[0]),
                        int(current_color[1]),
                        int(current_color[2])))

    # manually add the last entry to ensure it's exactly as entered
    palette.append(bright_color)

    return palette


def is_used(config):
    """Checks a config dictionary to see if this display module should be used.

    Args:
        config: A python dictionary
    Returns: Boolean as to whether the sections the DMD class needs are present.
    """

    # todo change to try
    if 'DMD' in config:
        return True
    else:
        return False


class DMD(MPFDisplay):
    """Base class for a traditional dot matrix display (DMD) in a pinball
    machine. This class is used to control a physical DMD connected via the
    14-pin header on the controller.

    Note that if you want to control a "color DMD", that is done via the Window
    display, not this DMD class. However if you would like to display a
    rendering of a traditional DMD in your on screen window, then you use this
    class to create the DMD display object.

    Args:
        machine: A reference to the main machine controller object.
    """

    def __init__(self, machine):
        if 'DMD' in machine.config:
            self.config = machine.config['DMD']
        else:
            self.config = dict()

        self.log = logging.getLogger('DMD')

        self.use_physical = False
        self.depth = 8
        self.color_dmd = False

        # Due to the way Pygame handles blits with 8-bit surfaces, we have to
        # have a standard palette that's the same for all of them and that's
        # 'known' so we can render fonts to known palette locations. This
        # palette is somewhat arbitrary but guarantees that everything we
        # render to this display will use the same palette.

        # todo change this to just use the screen DMD one, and set a default
        # in mpfconfig? That way we can do a blit instead of a PA when we render
        # it to a window? If we do that then we'll also have to change the
        # 1-bit display elements so they use the proper palette location.

        self.palette = [
            (0, 0, 0),
            (1, 0, 0),
            (2, 0, 0),
            (3, 0, 0),
            (4, 0, 0),
            (5, 0, 0),
            (6, 0, 0),
            (7, 0, 0),
            (8, 0, 0),
            (9, 0, 0),
            (10, 0, 0),
            (11, 0, 0),
            (12, 0, 0),
            (13, 0, 0),
            (14, 0, 0),
            (15, 0, 0)] * 16

        super(DMD, self).__init__(machine, self.config)
        self.name = 'DMD'

        if 'shades' not in self.config:
            self.config['shades'] = 16

        if 'physical' in self.config:
            self.use_physical = self.config['physical']
        else:
            self.use_physical = False

        if 'type' in self.config and self.config['type'] == 'color':
            self.color_dmd = True
            self.depth = 24

        if not self.color_dmd and self.use_physical:
            # Get a pointer to the physical DMD controller
            self.physical_dmd = self.machine.platform.configure_dmd()

        if self.color_dmd and self.use_physical:
            print "ERROR: You can't use a physical traditonal DMD as a color DMD."
            print "If you want an LCD screen to be a color DMD, then that is "
            print "done with the Window Manager."
            print "The physical setting here needs to be 'No' in this case."
            quit()

    def _initialize(self):
        # Internal method which initialized the DMD. This is separate from
        # __init__ because we have to wait until Pygame has been initialized

        super(DMD, self)._initialize()

        self.machine.display.default_display = self

    def update(self):
        """Automatically called based on a timer when the display should update.
        """

        super(DMD, self).update()

        # todo the P-ROC maintains a 3-frame buffer, so if we stop updating the
        # hardare when the surface is clean then it won't show until we send
        # another frame. So for the P-ROC we either need to send frames every
        # tick, or maintain a counter of the buffer so we can fill / flush it
        # with our clean image

        if self.use_physical:
            self.physical_dmd.update(self.current_slide.surface)

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
