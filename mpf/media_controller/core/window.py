"""Window manager which controls any pop up windows from MPF. Used to display
game information, status, tests, keyboard-to-switch mapping, on screen DMD,
etc."""
# window.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

try:
    import pygame
    import pygame.locals
except ImportError:
    pass

import version

from mpf.system.timing import Timing
from mpf.media_controller.core.display import MPFDisplay


class WindowManager(MPFDisplay):
    """Parent class for the Pygame-based on screen Window Manager in MPF.

    There is only one Window Manager per machine. It's used for lots of things,
    including displaying information about the game, an on-screen DMD, and for
    capturing key events which are translated to switches.
    """

    def __init__(self, machine):

        # move some of this to parent class

        if 'window' in machine.config:
            self.config = machine.config['window']
        else:
            self.config = dict()

        self.depth = 24
        self.palette = None

        super(WindowManager, self).__init__(machine, self.config)
        self.name = 'window'

        self.log = logging.getLogger("Window")
        self.log.debug("Loading the Window Manager")

        if 'window' in self.machine.config:
            self.config = self.machine.config['window']
        else:
            self.config = dict()

        self.slides = list()
        self.current_slide = None

        if 'title' not in self.config:
            self.config['title'] = ('Mission Pinball Framework v' +
                                    version.__version__)

        if 'resizable' not in self.config:
            self.config['resizable'] = True

        if 'fullscreen' not in self.config:
            self.config['fullscreen'] = False

        if 'frame' not in self.config:
            self.config['frame'] = True

        if 'quit_on_close' not in self.config:
            self.config['quit_on_close'] = True

        if 'background_image' not in self.config:
            self.config['background_image'] = None

        if 'fps' not in self.config or self.config['fps'] == 'auto':
            self.config['fps'] = Timing.HZ

        self._setup_window()

        self.machine.events.add_handler('init_phase_5',
                                        self._load_window_elements)

        # Block all Pygame events from being reported. We'll selectively enable
        # them one-by-one as event handlers are registered.
        pygame.event.set_allowed(None)

    def _initialize(self):
        super(WindowManager, self)._initialize()

        #self._load_window_elements()

    def _load_window_elements(self):
        # Loads the window elements from the config

        if 'elements' not in self.config:
            return

        self.config['elements'][0]['persist_slide'] = True
        self.config['elements'][0]['slide'] = 'default_window_slide'

        self.machine.display.slide_builder.build_slide(
            settings=self.config['elements'],
            display='window',
            priority=1)

    def _setup_window(self):
        # Sets up the Pygame window based on the settings in the config file.

        flags = 0

        if self.config['resizable']:
            flags = flags | pygame.locals.RESIZABLE

        if not self.config['frame']:
            flags = flags | pygame.locals.NOFRAME

        if self.config['fullscreen']:
            flags = flags | pygame.locals.FULLSCREEN

        # Create the actual Pygame window
        self.window = pygame.display.set_mode((self.width,
                                              self.height),
                                              flags)

        # Set the caption
        pygame.display.set_caption(self.config['title'])

    def update(self):
        """Updates the display. Called from a timer based on this display's fps
        settings.

        """
        super(WindowManager, self).update()

        # Update the display
        self.window.blit(self.current_slide.surface, (0, 0))
        pygame.display.flip()


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
