"""On screen window element for a virtual version of a DMD."""
# virtual_dmd.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import pygame
# todo make it so this doesn't crash if pygame is not available

from mpf.media_controller.core.display import DisplayElement
from mpf.system.config import Config
import mpf.media_controller.display_modules.dmd


class VirtualDMD(DisplayElement):
    """Represents an animation display element.

    Args:
        dmd_object: The DMD display object that this virtual DMD will use as its
            source.
        slide: The Slide object this animation is being added to.
        machine: The main machine object.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at: https://missionpinball.com/docs/displays/display-elements/positioning/

    """

    @classmethod
    def is_used(cls, config):
        # todo change to try
        if ('window' in config and 'elements' in config['window']
                and 'VirtualDMD' in config['window']['elements']):
            return True
        else:
            return False

    @property
    def dirty(self):
        return True
        # future optimization could be to return the dirty status of the source
        # DMD. We don't do that now because there would have to be some extra
        # intelligence to make sure it did one more loop as dirty after the
        # source turns clean. And really if the computer can't handle these
        # udpates then the fps is too high anyway, so we can ignore this.

    @dirty.setter
    def dirty(self, value):
        pass

    def __init__(self,  slide, machine, dmd_object=None, x=None, y=None, h_pos=None,
                 v_pos=None, layer=0, **kwargs):

        super(VirtualDMD, self).__init__(slide, x, y, h_pos, v_pos, layer)

        if not dmd_object:
            self.dmd_object = machine.display.displays['dmd']
        else:
            self.dmd_object = dmd_object

        self.config = kwargs

        self.name = 'VirtualDMD'

        if self.dmd_object.depth == 8:

            if 'pixel_color' not in kwargs:
                self.config['pixel_color'] = 'ff5500'

            if 'dark_color' not in self.config:
                self.config['dark_color'] = '221100'

            if 'pixel_spacing' not in self.config:
                self.config['pixel_spacing'] = 2

            # convert hex colors to list of ints
            self.config['pixel_color'] = Config.hexstring_to_list(
                self.config['pixel_color'])
            self.config['dark_color'] = Config.hexstring_to_list(
                self.config['dark_color'])

            # This needs to match the source DMD or it could get weird
            self.config['shades'] = self.dmd_object.config['shades']

            self.palette = mpf.media_controller.display_modules.dmd.create_palette(
                bright_color=self.config['pixel_color'],
                dark_color=self.config['dark_color'],
                steps=self.config['shades'])

        if ('width' in self.config and
                'height' not in self.config):
            self.config['height'] = self.config['width'] / 4
        elif ('height' in self.config and
                'width' not in self.config):
            self.config['width'] = self.config['height'] * 4
        elif ('width' not in self.config and
                'height' not in self.config):
            self.config['width'] = 512
            self.config['height'] = 128

        # Create a Pygame surface for the on screen DMD
        self.element_surface = pygame.Surface((self.config['width'],
                                      self.config['height']),
                                      depth=self.dmd_object.depth)

        if self.dmd_object.depth == 8:
            self.element_surface.set_palette(self.palette)

        self.layer = layer
        self.set_position(x, y, h_pos, v_pos)

    def update(self):
        """Updates the on screen representation of the physical DMD. This
        method automatically scales the surface as needed.
        """
        source_surface = pygame.PixelArray(self.dmd_object.get_surface()).surface

        pygame.transform.scale(source_surface,
                               (self.config['width'],
                                self.config['height']),
                               self.element_surface)

        ratio = self.element_surface.get_width() / float(source_surface.get_width())

        if self.config['pixel_spacing']:

            for row in range(source_surface.get_height() + 1):
                pygame.draw.line(self.element_surface, (0, 0, 0), (0, row*ratio),
                                 (self.config['width']-1, row*ratio),
                                 self.config['pixel_spacing'])

            for col in range(source_surface.get_width() + 1):
                pygame.draw.line(self.element_surface, (0, 0, 0), (col*ratio, 0),
                                 (col*ratio, self.config['height']-1),
                                 self.config['pixel_spacing'])

        self.decorate()
        return True  # since the virtual DMD is always dirty

display_element_class = VirtualDMD
create_asset_manager = False


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
