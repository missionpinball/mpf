"""A generic display interface which is used for all types of displays,
including DMD, LCD, alpha, segment, console, etc.."""
# display.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

# questions: where does the frame composition happen? At the display
# controller, or do we send all the individual little bits to the
# display interfaces?

import logging
import uuid

try:
    #os.environ['PYGAME_FREETYPE'] = '1'
    import pygame
    import pygame.locals
    #import pygame.freetype

except:
    pass

from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.display import *
from mpf.system.show_controller import ShowController


class DisplayController(object):
    """Parent class for the Display Controller in MPF. There is only one of
    these per machine. It's responsible for interacting with the display,
    regardless of what type it is (DMD, LCD, alphanumeric, etc.).
    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("DisplayController")
        self.log.debug("Loading the DisplayController")

        self.delay = DelayManager()

        self.surface = None  # The active Pygame display surface
        self.hw_module = None

        self.machine.request_pygame()

        # config defaults
        self.text_defaults = self.machine.config['DisplayDefaults']['TextElement']

        if ('font' not in self.text_defaults or
                self.text_defaults['font'] == 'None'):
            self.text_defaults['font'] = None

        if 'size' not in self.text_defaults:
            self.text_defaults['size'] = 22

        if 'opaque' not in self.text_defaults:
            self.text_defaults['opaque'] = True

        if 'v_align' not in self.text_defaults:
            self.text_defaults['v_align'] = 'center'

        if 'h_align' not in self.text_defaults:
            self.text_defaults['h_align'] = 'center'

        if 'x' not in self.text_defaults:
            self.text_defaults['x'] = 0

        if 'y' not in self.text_defaults:
            self.text_defaults['y'] = 0

        if 'time' not in self.text_defaults:
            self.text_defaults['time'] = 0
        else:
            self.text_defaults['time'] = (
                Timing.string_to_ms(self.text_defaults['time']))

        if 'color' not in self.text_defaults:
            self.text_defaults['color'] = 'ff0000'

        if 'shade' not in self.text_defaults:
            self.text_defaults['shade'] = 15

        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_display_modules)

    def set_default_surface(self, surface):
        """Sets the defauly Pygame surface that is used when display effects
        are called for.

        Args:
            surface: The pygame surface that will be used for the default
            surface.
        """

        self.surface = surface

    def _load_display_modules(self):
        # Load the display modules as specified in the config files

        # Look up the list of possible display mobuldes
        self.machine.config['MPF']['display_modules'] = (
            self.machine.config['MPF']['display_modules'].split(' '))

        # Loop through all the options to see which one (if any) are used
        for display in self.machine.config['MPF']['display_modules']:
            display_cls = eval(display)

            if display_cls.is_used(self.machine.config):
                self.hw_module = display_cls(self.machine)
                break
                # Right now we only support on type of display module at a time.
                # Should this change? todo

    def text(self, text, priority=0, time=None, replace=True, **kwargs):
        """Displays some text on the default display surface.

        Args:
            text: String of the text you want to display
            priority: Relative priority which controls z-order. (Not yet
            implemented.)
            time: MPF time string which specifies how long the text will be
            displayed before it's erased.
            replace: Not yet implemented
            font:
            size:
            opaque:
            v_align:
            h_align:
            x:
            y:
            color:
            shade:

        Note: As of now, font, size, and placement settings are ignored. It only
        has one font and it only displays text in one size, and it's all
        centered.

        """

        self.log.debug("Displaying Text: %s", text)

        if not self.surface:
            return  # todo temp.

        self.surface.fill((0, 0, 0))  # todo temp

        if 'font' in kwargs:
            fontname = kwargs['font']
        else:
            fontname = self.text_defaults['font']

        if 'size' in kwargs:
            size = kwargs['size']
        else:
            size = self.text_defaults['size']

        if 'opaque' in kwargs:
            opaque = kwargs['opaque']
        else:
            opaque = self.text_defaults['opaque']

        if 'v_align' in kwargs:
            v_align = kwargs['v_align']
        else:
            v_align = self.text_defaults['v_align']

        if 'h_align' in kwargs:
            h_align = kwargs['h_align']
        else:
            h_align = self.text_defaults['h_align']

        if 'x' in kwargs:
            x = kwargs['x']
        else:
            x = self.text_defaults['x']

        if 'y' in kwargs:
            y = kwargs['y']
        else:
            y = self.text_defaults['y']

        if 'time' in kwargs:
            time = Timing.string_to_ms(kwargs['time'])
        else:
            time = self.text_defaults['time']

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.text_defaults['color']

        if 'shade' in kwargs:
            shade = kwargs['shade']
        else:
            shade = self.text_defaults['shade']

        if self.surface.get_bitsize() == 8:
            color = self.surface.get_palette_at(shade)
        else:
            # convert color str to list todo
            pass

        font = pygame.font.Font(fontname, size)

        font = pygame.font.Font('mpf/fonts/Quadrit.ttf', 10)

        surface = font.render(text, False, color)

        # calculate rectangle size for that font
        width, height = surface.get_size()

        # temp center only
        x_pos = int((self.surface.get_width() - width) / 2)
        y_pos = int((self.surface.get_height() - height) / 2)

        self.surface.blit(surface, (x_pos, y_pos))

        if time:
            # set delay to come back with remove element
            self.delay.add(name=uuid.uuid4,
                           ms=time,
                           callback=self.remove_element)


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