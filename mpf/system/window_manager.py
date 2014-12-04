"""Window manager which controls any pop up windows from MPF. Used to display
game information, status, tests, keyboard-to-switch mapping, on screen DMD,
etc."""
# window_manager.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time

try:
    import pygame
    import pygame.locals
except ImportError:
    pass

import version

from mpf.system.show_controller import ShowController


class WindowManager(object):
    """Parent class for the Pygame-based on screen Window Manager in MPF.

    There is only one Window Manager per machine. It's used for lots of things,
    including displaying information about the game, an on-screen DMD, and for
    capturing key events which are translated to switches.
    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("Window")
        self.log.debug("Loading the Window Manager")

        if 'Window' in self.machine.config:
            self.config = self.machine.config['Window']
        else:
            self.config = dict()

        self.registered_handlers = dict()
        self.pygame_allowed_events = list()

        self.flip = False  # Should this display be flipped?
        self.secs_per_frame = 1
        self.next_frame_time = 0.0

        self.surface = None  # Ref to Pygame surface to display

        self.window_surfaces = set()

        if 'width' not in self.config:
            self.config['width'] = 800

        if 'height' not in self.config:
            self.config['height'] = 600

        if 'title' not in self.config:
            self.config['title'] = 'Mission Pinball Framework v' + version.__version__

        if 'resizeable' not in self.config:
            self.config['resizeable'] = True

        if 'fullscreen' not in self.config:
            self.config['fullscreen'] = False

        if 'frame' not in self.config:
            self.config['frame'] = True

        if 'quit_on_close' not in self.config:
            self.config['quit_on_close'] = True

        if 'fps' not in self.config:
            self.config['fps'] = 3

        if 'background_image' not in self.config:
            self.config['background_image'] = None

        self.secs_per_frame = 1.0 / self.config['fps']

        self.machine.events.add_handler('timer_tick', self._tick)

        self.log.debug("Setting up Pygame window. w:%s, h:%s, resizeable:%s, "
                       "frame: %s", self.config['width'], self.config['height'],
                       self.config['resizeable'], self.config['frame'])

        self._setup_window()

        # Block all Pygame events from being reported. We'll selectively enable
        # them one-by-one as event handlers are registered.
        pygame.event.set_allowed(None)

        # todo add frame, resizeable

        if self.config['quit_on_close']:
            pass  # todo

    def register_handler(self, event, handler):
        """Registers a method to be a handler for a certain type of Pygame
        event.

        Args:
            event: A string of the Pygame event name you're registering this
            handler for.
            handler: A method that will be called when this Pygame event is
            posted.
        """
        if event not in self.registered_handlers:
            self.registered_handlers[event] = set()

        self.registered_handlers[event].add(handler)
        self.pygame_allowed_events.append(event)

        self.log.debug("Adding Window event handler. Event:%s, Handler:%s",
                       event, handler)

        pygame.event.set_allowed(self.pygame_allowed_events)

    def set_window_surface(self, surface):
        """Specifies which Pygame Surface object should be used at the display
        Surface for the window.

        Args:
            surface: THe Pygame Surface you'd like to map to the display
                window.
            scale_to_fit: Whether the surface you're passing should be scaled
                up or down to fit in the display window. Note this will not
                change the aspect ratio.
        """

        self.surface = surface

    def _setup_window(self):
        # Sets up the Pygame window based on the settings in the config file.

        flags = 0

        if self.config['resizeable']:
            flags = flags | pygame.locals.RESIZABLE

        if not self.config['frame']:
            flags = flags | pygame.locals.NOFRAME

        if self.config['fullscreen']:
            flags = flags | pygame.locals.FULLSCREEN

        # Create the actual Pygame window
        self.window = pygame.display.set_mode((self.config['width'],
                                              self.config['height']),
                                              flags)

        # self.window is a Surface
        self.surface = self.window

        # Set the caption
        pygame.display.set_caption(self.config['title'])

        # Set the background image
        if self.config['background_image']:
            # Is the background image not a bmp?
            if not self.config['background_image'].endswith('bmp'):
                # If so, can we load non-bitmaps?
                if not pygame.image.get_extended():
                    return

            background = pygame.image.load(
                self.config['background_image'])
            background_rect = background.get_rect()
            self.surface.blit(background, background_rect)

    def _tick(self):
        # Called once per machine loop. Used to update the display and collect
        # key and mouse events

        # Get key & mouse events
        for event in pygame.event.get():
            if event.type in self.registered_handlers:
                for handler in self.registered_handlers[event.type]:
                    handler(event.key, event.mod)
                    # todo change above to kwargs?

        # Update the surfaces
        current_time = time.time()
        if self.next_frame_time <= current_time:

            # Get the hw_module to update its screen surface
            if self.machine.display.hw_module:
                self.machine.display.hw_module.update_screen()

            for surface in self.window_surfaces:
                self.surface.blit(surface.surface, (surface.x, surface.y))

            pygame.display.flip()
            self.next_frame_time = current_time + self.secs_per_frame


class WindowSurface(object):
    """Parent class for a Pygame surface which will be included in the on screen
    display window.

    Args:
        config: Python dictionary which holds the configuration for this
        surface.
        surface: A reference to the Pygame surface which this WindowSurface is
        based on.
        window_manager: A reference to the machine controller's WindowManager
        object.
    """

    def __init__(self, config, surface, window_manager):

        self.window_manager = window_manager
        self.config = config
        self.surface = surface
        self.dirty = True

        # figure out the position
        win_w = self.window_manager.config['width']
        win_h = self.window_manager.config['height']
        w = config['width']
        h = config['height']
        self.x = 0
        self.y = 0

        if type(self.config['h_pos']) is int:
            self.x = self.config['h_pos']
        else:
            self.x = (win_w - w) / 2

        if type(self.config['v_pos']) is int:
            self.y = self.config['v_pos']
        else:
            self.y = (win_h - h) / 2

        if 'border_color' in self.config:
            self.border_color = ShowController.hexstring_to_list(
                self.config['border_color'])
        else:
            self.border_color = (255, 255, 255)

        if self.config['border_width']:
            pygame.draw.rect(self.window_manager.surface,
                             self.border_color,
                             (self.x-self.config['border_width'],
                              self.y-self.config['border_width'],
                              w+(self.config['border_width']),
                              h+(self.config['border_width'])),
                             self.config['border_width'])

        # todo do we need a way to remove these?

        self.window_manager.window_surfaces.add(self)

        def update(self):
            # todo, not yet implemented

            if self.dirty:
                pass
                self.dirty = False
        # todo this does nothing yet

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