"""Image class which is a DisplayElement which shows images on the display."""
# image.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import pygame
import pygame.locals

from mpf.media_controller.core.display import DisplayElement
import mpf.media_controller.display_modules.dmd
from mpf.media_controller.core.assets import Asset

dmd_palette = [(0, 0, 0),
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


class Image(Asset):

    def _initialize_asset(self):

        if 'alpha_color' in self.config:
            self.alpha_color = (self.config['alpha_color'])
        else:
            self.alpha_color = None

        if 'target' in self.config:
            self.target = self.config['target']
        else:
            self.target = None

        self.image_surface = None

    def save_image(self, surface, filename):
        """ Saves an image to disk.

        This menthod is not yet imlpemented.

        """
        image_string = pygame.image.tostring(surface, 'P')
        from_surface = pygame.image.fromstring(image_string, (128, 32), 'P')

    def save_image_to_dmd(self):
        """ Saves an image to disk in the DMD file format.

        This menthod is not yet imlpemented.

        """
        pass

    def _load(self, callback):

        if self.file_name.endswith('.dmd'):
            self.image_surface = mpf.display_modules.dmd.load_dmd_file(
                file_name=self.file_name,
                palette=dmd_palette,
                alpha_color=self.alpha_color)
            self.image_surface = self.image_surface[0]
            self.loaded = True

        else:

            try:
                self.image_surface = pygame.image.load(self.file_name)
            except pygame.error:
                self.asset_manager.log.error("Pygame Error for file %s. '%s'",
                                             self.file_name, pygame.get_error())
            except:
                raise

            if self.target == 'dmd':
                # This image will be shown on the DMD, so we need to convert its
                # surface to the DMD format
                self.image_surface = display_modules.dmd.surface_to_dmd(
                    surface=self.image_surface,
                    alpha_color=self.alpha_color)
                # todo add shades here if we ever support values other than 16

        self.loaded = True

        if callback:
            callback()

        # todo:
        # depth
        # w, h
        # load from image file

    def _unload(self):
        self.image_surface = None
        #self.loaded = False


class ImageDisplayElement(DisplayElement):

    """Represents an image display element.

    Args:
        slide: The Slide object this image is being added to.
        machine: The main machine object.
        image: The name of the registered image element you'd like to show
        width: The width of the image. A value of None means that it
            will display at its native width.
        height: The height of the image. A value of None means that it
            will display at its native height.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at: https://missionpinball.com/docs/displays/display-elements/positioning/

    """

    def __init__(self, slide, machine, image, width=None, height=None, x=None,
                 y=None, h_pos=None, v_pos=None, layer=0, **kwargs):

        super(ImageDisplayElement, self).__init__(slide, x, y, h_pos, v_pos,
                                                  layer)

        self.loadable_asset = True
        self.machine = machine

        if image not in machine.images:
            self.log.critical("Received a request to add an image, but "
                              "the name '%s' doesn't exist in in the list of "
                              "registered images.", image)
            raise Exception("Received a request to add an image, but "
                             "the name '%s' doesn't exist in in the list of "
                             "registered images.", image)
        else:
            self.image = machine.images[image]

        # todo implement width and height restrictions

        self.layer = layer

        if self.image.loaded:
            self._asset_loaded()
        else:
            self.ready = False
            self.image.load(callback=self._asset_loaded)

    def _asset_loaded(self):

        self.element_surface = self.image.image_surface
        self.set_position(self.x, self.y, self.h_pos, self.v_pos)
        self.ready = True

        super(ImageDisplayElement, self)._asset_loaded()

asset_class = Image
asset_attribute = 'images'  # self.machine.<asset_attribute>
display_element_class = ImageDisplayElement
create_asset_manager = True
path_string = 'images'
config_section = 'Images'
file_extensions = ('png', 'jpg', 'jpeg', 'bmp', 'dmd')


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
