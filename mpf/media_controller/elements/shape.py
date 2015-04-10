"""Shape class which is a DisplayElement that draws simple shapes on the
screen."""
# shape.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import pygame
import pygame.locals

from mpf.media_controller.core.display import DisplayElement


class Shape(DisplayElement):

    """Represents an animation display element.

    Args:
        slide: The Slide object this animation is being added to.
        machine: The main machine object.
        shape: The name of the shape you'd like to draw. See notes below.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.
        **kwargs: Additional keyword arguments which vary depending on the shape
            you're drawing.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at: https://missionpinball.com/docs/displays/display-elements/positioning/

    Shapes options:

    box: Draws a box.

    Additional keywords:
        width: The width of the box.
        height: The height of the box.
        thickness: How many pixels thick you want the box to be. A value of 0
            means the box will be filled in solid.

    line: Draws a line.

    Additional keywords:
        start_x, start_y: The coordinates of the starting point.
        end_x, end_y: The coordinates of the ending point.
        thickness: How many pixels thick you want the line to be.

    """

    def __init__(self, slide, machine, shape, x=None, y=None, h_pos=None,
                 v_pos=None, layer=0, **kwargs):

        super(Shape, self).__init__(slide, x, y, h_pos, v_pos, layer)

        self.slide = slide
        self.shape = shape

        if 'name' in kwargs:
            self.name = kwargs['name']
        else:
            self.name = 'Shape'

        self.adjust_colors(**kwargs)

        if 'thickness' not in kwargs:
            kwargs['thickness'] = 1

        if shape == 'box':
            self.box(width=kwargs['width'],
                      height=kwargs['height'],
                      thickness=kwargs['thickness'])

        elif shape == 'line':
            self.line(end_x=kwargs['width'],
                      end_y=kwargs['height'],
                      thickness=kwargs['thickness'])
        else:
            self.machine.log.critical("Invalid shape: ", shape)
            raise Exception()

        # todo change to arg
        self.element_surface.set_colorkey((0, 0, 0))

        self.layer = layer
        self.set_position(x, y, h_pos, v_pos)

    def box(self, width, height, thickness):

        self.create_element_surface(width, height)

        pygame.draw.rect(self.element_surface, self.adjusted_color,
                         (0, 0, width, height), thickness)

    def line(self, start_x, start_y, end_x, end_y, thickness):

        self.create_element_surface(abs(start_x - end_x),
                                    abs(start_y - end_y))

        pygame.draw.line(self.element_surface, self.adjusted_color,
                         (start_x, start_y), (end_x, end_y), thickness)

display_element_class = Shape
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
