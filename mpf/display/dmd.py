"""MPF display plugin the dot matrix display, used for both physical and on-
screen DMDs."""
# dmd.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import pygame
import logging
# todo make it so this doesn't crash if pygame is not available

from mpf.system.show_controller import ShowController
from mpf.system.window_manager import WindowSurface


class DMD(object):
    """Base class for a traditional dot matrix display (DMD) in a pinball
    machine. This class is used to control a physical DMD connected via the
    14-pin header on the controller, and also to create an on-screen
    representation of that DMD in a Window.

    Note that if you want to control a "color DMD", that's actually and LCD
    screen which means you'd use the LCD class (with a filter to make it look
    like dots), not this DMD class.

    Args:
        machine: A reference to the main machine controller object.
    """

    @classmethod
    def is_used(cls, config):
        # todo change to try
        if 'DMD' in config or ('Window' in config and 'elements' in config['Window']
                             and 'DMD' in config['Window']['elements']):
            return True
        else:
            return False

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('DMD')

        self.screen_surface = None
        self.use_physical = False
        self.use_screen = False

        # read in config
        # todo see if the user has manually configured a color map
        # todo if not, then look for the color here

        self.config = self.machine.config['DMD']

        try:
            if 'DMD' in self.machine.config['Window']['elements']:
                self.window_config = (
                    self.machine.config['Window']['elements']['DMD'])
                self.use_screen = True
        except:
            self.window_config = dict()
            self.use_screen = False

        if 'width' not in self.config:
            self.config['width'] = 128

        if 'height' not in self.config:
            self.config['height'] = 32

        if 'shades' not in self.config:
            self.config['shades'] = 16

        # On screen DMD config
        if self.use_screen:
            if 'pixel_color' not in self.window_config:
                self.window_config['pixel_color'] = 'ff5500'

            if 'dark_color' not in self.window_config:
                self.window_config['dark_color'] = '000000'

            if ('width' in self.window_config and
                    'height' not in self.window_config):
                self.window_config['height'] = self.window_config['width'] / 4
            elif ('height' in self.window_config and
                    'width' not in self.window_config):
                self.window_config['width'] = self.window_config['height'] * 4
            elif ('width' not in self.window_config and
                    'height' not in self.window_config):
                self.window_config['width'] = 512
                self.window_config['height'] = 128

        if 'physical' in self.config:
            self.use_physical = self.config['physical']
        else:
            self.use_physical = True

        if not self.use_screen and not self.use_physical:
            self.log.warning("DMD configuration found, but both 'physical' is "
                             "False and no DMD Window elements were found, "
                             "so no DMD will be used.")
            return False

        self.machine.events.add_handler('pygame_initialized', self._initialize)

    def _initialize(self):
        # Internal method which initialized the DMD. This is separate from
        # __init__ because we have to wait until Pygame has been initialized

        if self.use_screen:
            self._setup_screen()

        # Set up the physical even if we don't have a physical DMD. Why? Because
        # the screen DMD needs to know the physical DMDs 'native' settings, like
        # resolution and shades, so it knows how to render the on screen version
        self._setup_physical()

        # setup the default surface
        if self.use_physical:
            self.surface = self.physical_surface
        else:
            self.surface = self.screen_surface

        # We need to set up a palette so the shading works properly, even if
        # there's no on screen DMD.

        # convert hex colors to list of ints
        bright_color = ShowController.hexstring_to_list(
            self.window_config['pixel_color'])
        dark_color = ShowController.hexstring_to_list(
            self.window_config['dark_color'])

        palette = self.create_palette(
            bright_color=bright_color,
            dark_color=dark_color,
            steps=self.config['shades'])

        # now set this surface to use this newly-created palette

        if self.use_physical:
            self.physical_surface.set_palette(palette)

        if self.use_screen:
            self.screen_surface.set_palette(palette)

        # set this surface as the machine's primary surface
        if self.use_physical:
            self.machine.display.set_default_surface(self.physical_surface)
        else:
            self.machine.display.set_default_surface(self.screen_surface)

        self.machine.events.add_handler('timer_tick', self._tick)

    def _setup_physical(self):
        # Sets up the physical DMD hardware

        # Get a pointer to the physical DMD controller
        self.physical_dmd = self.machine.platform.configure_dmd()

        # platform config will return False if no DMD support
        if self.physical_dmd:

            # Create a Pygame surface for the physical DMD
            self.physical_surface = pygame.Surface((self.config['width'],
                                                    self.config['height']),
                                                   depth=8)
        else:
            self.use_physical = False

    def _setup_screen(self):
        # Sets up the on screen representation of a traditional DMD

        # Make sure the machine controller has a window manager instance
        #self.machine.request_pygame()
        #self.window = self.machine.get_window()
        self.machine.get_window()  # todo do we need to save a ref here?

        # Create a Pygame surface for the on screen DMD
        self.screen_surface = pygame.Surface((self.window_config['width'],
                                              self.window_config['height']),
                                             depth=8)
        self.surface = self.screen_surface

        WindowSurface(self.window_config, self.surface,
                      self.machine.window_manager)
        # todo do we need to save a ref?

    def _tick(self):
        # Called once per machine loop

        # see if the surface has changed
        # if so, update it.

        self.surface.blit(self.machine.display.surface, (0, 0))

        self.update_physical(self.surface)

    def update_physical(self, surface):
        """Updates the physical DMD with the Pygame surface that is passed to
        it.

        Args:
            surface: A Pygame surface that will be written to the physical DMD.

        Note: The Pygame surface passed must have a color depth of 8-bits, and
        the physical DMD will only read integer values 0 through the bit depth
        of the DMD, typically 4 (meaning it only looks for values 0-3) or 16
        (meaning it looks for 0-15). Any value higher than that will be rendered
        as full brightness.
        """
        if self.use_physical:
            self.physical_dmd.update(surface)

    def update_screen(self):
        """Updates the on screen representation of the physical DMD. This
        method automatically scales the surface as needed.
        """

        if self.use_physical:

            pygame.transform.scale(self.physical_surface,
                                   (self.window_config['width'],
                                    self.window_config['height']),
                                   self.screen_surface)

    def create_palette(self, dark_color=[0, 0, 0], bright_color=[255, 0, 0],
                       steps=16):
        """Returns a Pygame palette based on the colors passed to it.

        Args:
            dark_color: A list of three integers (0-255 each) which represents
            the RGB values of the dark (or "off") color of a pixel. Default is
            [0, 0, 0] (black).
            bright_color: A list of three integers (0-255 each) which represents
            the RGB values of a fully bright (full "on") color of a pixel.
            Default is [255, 0, 0] (red).
            steps: An integer which is the number of steps (or shades) in the
            palette. Typical values are 2 (1-bit color), 4 (2-bit color), or 16
            (4-bit color). Default is 16.

        Returns:
            A Pygame palette which is a list of three-item lists. The first
            item will always be the dark_color, and the last item will always
            be the bright_color. The values in between are the steps.
            """

        palette = []
        step_size = [bright_color[0] / (steps - 1.0),
                     bright_color[1] / (steps - 1.0),
                     bright_color[2] / (steps - 1.0)
                     ]

        current_color = dark_color

        # manually add the first entry to ensure it's exactly as entered
        palette.append([int(current_color[0]),
                        int(current_color[1]),
                        int(current_color[2])])

        # calculate all the middle values (all except the dark and bright)
        for i in range(steps-2):
            current_color[0] += step_size[0]
            current_color[1] += step_size[1]
            current_color[2] += step_size[2]
            palette.append([int(current_color[0]),
                            int(current_color[1]),
                            int(current_color[2])])

        # manually add the last entry to ensure it's exactly as entered
        palette.append(bright_color)

        return palette

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