"""Contains the parent classes for MPF's FontManager."""

# font_manager.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os

import pygame

class FontManager(object):
    """Parent class of the Font Manager.

    Args:
        machine: The MachineController.
        config: Dictionary of the font configuration.

    Attributes:
        font_cache: Dictionary of Pygame font rendering objects.

    """

    def __init__(self, machine, config):

        self.log = logging.getLogger('Fonts')

        self.machine = machine
        self.config = config
        self.font_cache = dict()

        # todo add setting to preload them?
        # todo add setting to fail if font/size combo not found

    def render(self, text, font='default', antialias=False, size=None,
               color=None, bg_color=None, alpha_color=None,
               alpha_channel=None, **kwargs):


        font_obj = self.get_font(font, size)

        if bg_color is not None:
            surface = font_obj.render(text, antialias, color, bg_color)
        else:
            surface = font_obj.render(text, antialias, color)

        # if alpha, do something to the surface # todo

        # crop the surface
        start_y = 0
        end_y = surface.get_height()

        if 'crop_top' in self.config[font]:
            start_y = self.config[font]['crop_top']

        if 'crop_bottom' in self.config[font]:
            end_y -= (self.config[font]['crop_bottom'] + start_y)

        return surface.subsurface((0, start_y, surface.get_width(), end_y))

    def add_to_cache(self, font, size, font_obj):
        """Adds a Pygame font object to the font cache.

        Args:
            font_name: String of what you want to refer to this font as.
            size: Actual size this font object renders at.
            font_obj: The Pygame font object that will be cached.

        """
        try:
            size = int(size)
        except:
            size = 0

        if font not in self.font_cache:
            self.font_cache[font] = dict()

        if size not in self.font_cache[font]:
            self.font_cache[font][size] = font_obj

    def get_font(self, font=None, size=None, cache=True):
        """Returns a Pygame font rendering object for a given font name and
        size. Checks cache first and then falls back to disk. Optionally caches
        new font objects for reuse.

        Args:
            name: String name of the font requested.
            size: Integer of the MPF size of the font you want.
            cache: Boolean as to whether the ront rendering object that's
                created should be cached.

        Returns: A Pygame font rendering object.

        """

        if font in self.font_cache and size in self.font_cache[font]:
            return self.font_cache[font][size]

        else:
            if font in self.config:

                if not size:
                    size = self.config[font]['size']

                font_file = self.locate_font_file(self.config[font]['file'])

                self.log.debug("Loading font '%s' at size %s.", font, size)

                # todo load the file first to make sure it's valid
                font_obj = pygame.font.Font(font_file, size)

                if cache:
                    self.add_to_cache(font, size, font_obj)

            return font_obj

    def locate_font_file(self, file_name):
        """Takes a file name and tries to find the font file on disk. First it
        checks the machine_folder fonts folder to see if there's a machine-
        specific font, then it tries the MPF system fonts folder.

        Args:
            file_name: String of the font file name

        Returns: String of the full path (path + file name) of the font.
        """

        if not file_name:
            return

        full_path = os.path.join(self.machine.machine_path,
                                 self.machine.config['MediaController']['paths']
                                 ['fonts'],
                                 file_name)
        if os.path.isfile(full_path):
            return full_path
        else:
            full_path = os.path.join('mpf', 'media_controller', 'fonts',
                                     file_name)
            if os.path.isfile(full_path):
                return full_path
            else:
                self.log.warning("Could not locate font file '%s'. Default font"
                                 "will be used instead.", file_name)

# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

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
