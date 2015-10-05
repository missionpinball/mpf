"""Contains the parent classes for MPF's display system, including the
DisplayController, MPFDisplay, DisplayElement, Transition, and Decorator.
"""

# display.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time

try:
    import pygame
    import pygame.locals

except ImportError:
    pass

from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing, Timer
from mpf.system.assets import AssetManager
from mpf.system.config import Config
from mpf.media_controller.core.slide import Slide
from mpf.media_controller.core.font_manager import FontManager
from mpf.media_controller.core.slide_builder import SlideBuilder
import mpf.media_controller.decorators
import mpf.media_controller.transitions


class DisplayController(object):
    """Parent class for the Display Controller in MPF. There is only one of
    these per machine. It's responsible for interacting with the display,
    regardless of what type it is (DMD, LCD, alphanumeric, etc.).

    Args:
        machine: The main MachineController object.
    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("DisplayController")
        self.log.debug("Loading the DisplayController")

        self.delay = DelayManager()

        self.hw_module = None
        self.fonts = None

        self.machine.request_pygame()

        # todo move this? Should be in the DMD module?
        self.dmd_palette = [(0, 0, 0),
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

        self.transitions = dict()
        self.decorators = dict()
        self.display_elements = dict()

        self.displays = dict()
        self.default_display = None
        self.slide_builder = SlideBuilder(self.machine)

        # Register for events
        if 'window' in self.machine.config:
            self.machine.events.add_handler('init_phase_2',
                                            self.machine.get_window,
                                            priority=1000)

        self.machine.events.add_handler('init_phase_1',
                                        self._load_display_modules)
        self.machine.events.add_handler('init_phase_1',
                                        self._load_display_element_modules)
        self.machine.events.add_handler('init_phase_1',
                                        self._load_fonts)
        self.machine.events.add_handler('init_phase_1',
                                        self._load_transitions)
        self.machine.events.add_handler('init_phase_1',
                                        self._load_decorators)

        if 'slide_player' in self.machine.config:
            self.machine.events.add_handler('pygame_initialized',
                self._load_slide_builder_config)

    def _load_slide_builder_config(self):
        # This has to be a separate method since slide_builder.process config
        # returns an unloader method so we can't use it as an event handler
        self.slide_builder.process_config(
            self.machine.config['slide_player'], priority=0)

    def _load_display_modules(self):
        # Load the display modules as specified in the config files

        # todo this could be cleaned up a bit

        self.machine.config['media_controller']['display_modules']['modules'] = (
            self.machine.config['media_controller']['display_modules']
            ['modules'].split(' '))

        for module in (self.machine.config['media_controller']['display_modules']
                       ['modules']):
            i = __import__('mpf.media_controller.display_modules.' +
                           module.split('.')[0], fromlist=[''])

            if i.is_used(self.machine.config):
                self.hw_module = getattr(i, module.split('.')[1])(self.machine)
                return  # we only support one type of hw_module at a time

    def _load_display_element_modules(self):

        # adds the available display elements to the list
        # creates asset managers for display assets that need them

        for module in (self.machine.config['media_controller']['display_modules']
                       ['elements']):

            display_element_module = __import__('mpf.media_controller.elements.'
                                                + module, fromlist=[''])
            self.display_elements[module] = display_element_module

            if display_element_module.create_asset_manager:
                AssetManager(
                    machine=self.machine,
                    config_section=display_element_module.config_section,
                    path_string=(self.machine.config['media_controller']['paths']
                                  [display_element_module.path_string]),
                    asset_class=display_element_module.asset_class,
                    asset_attribute=display_element_module.asset_attribute,
                    file_extensions=display_element_module.file_extensions)

    def _load_fonts(self):
        if 'fonts' not in self.machine.config:
            self.machine.config['fonts'] = dict()

        self.fonts = FontManager(self.machine, self.machine.config['fonts'])

    def _load_transitions(self):
        # This is tricky because we don't want to import them, rather, we just
        # want to create a list of them.

        # todo this could be cleaned up by adding module attributes which point
        # to the classes in the module

        for k, v in (self.machine.config['media_controller']['display_modules']
                     ['transitions'].iteritems()):
            __import__('mpf.media_controller.transitions.' + v.split('.')[0])
            module = eval('mpf.media_controller.transitions.' + v.split('.')[0])
            cls = v.split('.')[1]
            self.transitions[k] = (module, cls)

    def _load_decorators(self):
        # This is tricky because we don't want to import them, rather, we just
        # want to list them.

        # todo this could be cleaned up by adding module attributes which point
        # to the classes in the module

        for k, v in (self.machine.config['media_controller']['display_modules']
                     ['decorators'].iteritems()):
            __import__('mpf.media_controller.decorators.' + v.split('.')[0])
            module = eval('mpf.media_controller.decorators.' + v.split('.')[0])
            cls = v.split('.')[1]
            self.decorators[k] = (module, cls)

    def set_default_display(self, display_name):
        """Sets the default display.

        Args:
            display_name: String name of the display you'd like to set to be
                the default.

        Returns: None on success, False on failure.

        """

        if display_name in self.displays:
            self.default_display = self.displays[display_name]

        else:
            return False




class MPFDisplay(object):
    """Parent class for a display device. (e.g. DMD, on screen display,
    segmented display, etc.)

    Args:
        machine: The main MachineController instance.
        config: Dictionary of config settings for this display isntance.

    Attributes:
        width: Integer value of the width of this display, in pixels.
        height: Integer value of the height of this display, in pixels.
        depth: Integer color depth for this display, either 8 or 24.
        slides: Dictionary of slides for this frame. Keys are slide names,
            values are slide objects.
        current_slide: Reference to the current slide that this display is
            showing.
        flag_active_transition: Boolean of whether there's an active transition
            taking place on this display.
        name: String name of this display. Default is 'MPFDisplay'.
        surface: Pygame surface that this display uses.

    """

    def __init__(self, machine, config=None):
        self.machine = machine

        self.log = logging.getLogger('MPFDisplay')

        if config:
            self.config = config
        else:
            self.config = dict()

        if 'debug' in config and config['debug']:
            self.debug = True
        else:
            self.debug = False

        if 'width' not in self.config:
            self.width = 800
        else:
            self.width = self.config['width']

        if 'height' not in self.config:
            self.height = 600
        else:
            self.height = self.config['height']

        if 'fps' not in self.config or self.config['fps'] == 'auto':
            self.config['fps'] = Timing.HZ

        self.slides = list()
        self.current_slide = None
        self.flag_active_transition = False
        self.transitions = self.machine.display.transitions
        self.surface = None
        self.depth = None
        self.palette = None
        self.transition_dest_slide = None
        self.transition_slide = None
        self.transition_object = None

        self.name = 'MPFDisplay'

        if not self.machine.display.default_display:
            self.machine.display.default_display = self

        self.machine.events.add_handler('pygame_initialized', self._initialize)

    def __repr__(self):
        return '<Display.{}>'.format(self.name)

    def _initialize(self):
        """Internal method which initializes this display. This is separate from
        # __init__ because we have to wait until Pygame has been initialized.
        """

        # Create a default surface for this display
        self.surface = pygame.Surface((self.width, self.height),
                                      depth=self.depth)

        if self.depth == 8:
            self.surface.set_palette(self.palette)

        self.machine.display.displays[self.name] = self

        if not self.machine.display.default_display:
            self.machine.display.default_display = self

        self.create_blank_slide()

        self.machine.timing.add(
            Timer(self.update, frequency=1/float(self.config['fps'])))

    def create_blank_slide(self):
        """Creates a new blank slide and adds it to the list of slides for this
        display.

        """
        self.add_slide(Slide(mpfdisplay=self, priority=0, persist=True,
                             machine=self.machine, name='blank'))

    def add_slide(self, slide, transition_name=None, transition_settings=None):
        if transition_name or transition_settings:
            self._create_transition(slide, transition_name,
                                    transition_settings)

        else:
            self.slides.append(slide)
        self.sort_slides()
        self.refresh()

    def sort_slides(self):
        self.slides.sort(key=lambda x: (x.priority, x.id),
                         reverse=True)

    def remove_slide(self, slide, force=False, refresh_display=True):
        """Removes a slide by slide object, but only if that slide (1) is not
        set to persist, (2) is not involved in an active transition, and (3) is
        not the only slide from its mode.

        """

        if not slide:
            return

        if slide in self.slides and (force or (not slide.persist and
                                     not slide.active_transition and
                                     not self.is_only_slide_from_mode(slide))):

            slide.remove(refresh_display=refresh_display)

    def remove_slides(self, slides, force=False, refresh_display=True):
        for slide in slides:
            self.remove_slide(slide, force, refresh_display)

    def refresh(self):
        self.remove_stale_slides()
        self.current_slide = self.slides[0]

        self.log.debug("Total number of slides: %s", len(self.slides))

    def remove_stale_slides(self):
        """Searches through all the active slides and only keeps one slide per
        mode. Will also keep slides that are set to persist=True and will keep
        slides that are actively involved in a transition.

        Slides that have an expire time do not count as the "one slide per
        mode" since we want to make sure a permanent slide is there when the
        expiring slide expires.

        """
        found_slides_from_modes = list()
        slides_to_remove = list()
        slides_to_kill = list()

        for slide in self.slides:
            if (not slide.persist and
                    not slide.expire_ms and
                    not slide.active_transition and
                    slide.mode in found_slides_from_modes):
                slides_to_remove.append(slide)
            elif not slide.expire_ms:
                found_slides_from_modes.append(slide.mode)

            if not slide.surface:
                slides_to_kill.append(slide)

        for slide in slides_to_remove:
            slide.remove(refresh_display=False)

        for slide in slides_to_kill:
            try:
                self.slides.remove(slide)
            except ValueError:
                pass

    def get_slide_by_name(self, name):
        try:
            return next(x for x in self.slides if x.name == name)

        except StopIteration:
            return None

    def _create_transition(self, new_slide, transition_name=None,
                           transition_settings=None):
        if not transition_name:
            transition_name = transition_settings['type']

        if not new_slide.ready():
            new_slide.add_ready_callback(self._create_transition,
                                         new_slide=new_slide,
                                         transition_name=transition_name,
                                         transition_settings=transition_settings)
            new_slide.active_transition = True

        else:
            transition_class = eval('mpf.media_controller.transitions.' +
                                    transition_name + '.' +
                                    self.transitions[transition_name][1])
            self.transition_slide = (
                transition_class(mpfdisplay=self,
                                 machine=self.machine,
                                 slide_a=self.current_slide,
                                 slide_b=new_slide,
                                 priority=new_slide.priority + 1,
                                 mode=new_slide.mode,
                                 **transition_settings))

            self.slides.append(self.transition_slide)
            self.slides.append(new_slide)

    def transition_complete(self):
        """Tells the display that the current transition is complete and
        switches the display over to the destination slide.

        This method is automatically called when a transition ends. It can
        safely be called during a transition to end it early.

        """
        self.flag_active_transition = False
        self.transition_dest_slide = None
        self.transition_slide = None
        self.transition_object = None

    def is_only_slide_from_mode(self, slide):
        """Checks to see if the slide passed is the only slide in a mode.

        Args:
            slide: A Slide object

        Returns True if this is the only slide in a mode, False if there are
        other slides from that mode.

        """

        slides = [x.mode for x in self.slides]

        if slides.count(slide.mode) == 1:
            return True
        else:
            return False

    def update(self):
        """Updates the contents of the current slide. This method can safely
        be called frequently.

        """
        self.current_slide.update()

    def get_surface(self):
        """Returns the surface of the current slide."""
        return self.current_slide.surface


class DisplayElement(object):
    """Parent class for all display elements.

    Display Elements are objects that are placed onto a slide. Examples of
    display elements include Text, Image, Shape, Animation, Movie, etc.

    Attributes:
        dirty: Boolean as to whether this element is dirty. True means that
            this element has been updated and the slide needs to be
            re-rendered. When the slide updates itself with the latest content
            from this element, it sets dirty to False.
        opacity: 0-255 integer of how translucent this element is. 255 is fully
            opaque. 0 is fully translucent (i.e. invisible).
        surface: The pygame surface that makes up this element.
        slide: The Slide object this element belongs to.
        adjusted_color: The properly formatted object color based on the shade
            or hex color string specified in the settings for this display
            element.
        adjusted_bg_color: The properly formatted background color based on the
            shade or hex color string specified in the settings for this
            display element.
        rect: The Pygame Rect object which defines this elements's size and
            position on the parent slide.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    """

    def __init__(self, slide, x, y, h_pos, v_pos, layer):

        self.decorators = list()
        self.dirty = True
        self.rect = None
        self.slide = slide
        self._opacity = 255
        self.name = None
        self.loadable_asset = False
        self.notify_when_loaded = set()
        self.loaded = False

        self.x = x
        self.y = y
        self.h_pos = h_pos
        self.v_pos = v_pos
        self.layer = layer
        self.adjusted_color = None
        self.adjusted_bg_color = None

        self.ready = True

        # be sure to call set_position() in your __init__ if you subclass this

    @property
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):

        # todo temp. Need to change to variable opacity blitting

        if value == 0:
            self._opacity = 0
            #self.clear()
        else:
            self._opacity = 255
            #self.show()

    @property
    def surface(self):
        if self.opacity == 0:
            return self.get_background()
        elif self.opacity == 255:
            return self.element_surface

    def _notify_when_loaded(self, callback):
        if self.loaded:
            callback(self)
        else:
            self.notify_when_loaded.add(callback)

    def _asset_loaded(self):
        for callback in self.notify_when_loaded:
            callback(self)

    def update(self):
        """Called when the display wants to update itself. Updates this
        element's surface as well as applies decorators.

        Returns: True if an update was made that requires re-blitting. Otherwise
            False.

        """

        # If you subclass this be sure to set self.dirty and to call decorate()

        if self.decorate() or self.dirty:
            self.dirty = False
            return True
        else:
            return False

    def decorate(self):
        updated = False
        for decorator in self.decorators:
            if decorator.update():
                updated = True

        return updated

    def set_position(self, x=None, y=None, h_pos=None, v_pos=None):
        """Calculates the x,y position for the upper-left corner of this element
        based on several positioning parameters.

        Args:
            v_pos: String which decribes the vertical anchor position this
                calculation should be based on. Options include 'top', 'bottom',
                and 'center' (or 'middle'). Default is 'center' if no `y`
                parameter is given, and 'top' if there is a `y` parameter.
            h_pos: String which describes the horizontal anchor position this
                calculation should be based on. Options include 'left', 'right',
                and 'center' (or 'middle'). Default is 'center' if no `x`
                parameter is given, and 'left' if there is an `x` parameter.
            x: The x (horizontal value) you'd like to position this element in.
                If this is an positive integer, it will be the number of pixels
                to the left of the h_pos anchor. If it's negative, it will be
                the number of pixels to the right of the h_pos anchor. If this
                is a float between -1.0 and 1.0, then this will be the percent
                between the left edge and the h_pos anchor for positive values,
                and the right edge and the h_pos anchor
                for negative values.
            y: The y (veritcal value) you'd like to position this element in.
                If this is an positive integer, it will be the number of pixels
                below the v_pos anchor. If it's negative, it will be
                the number of pixels above the v_pos anchor. If this
                is a float between -1.0 and 1.0, then this will be the percent
                between the bottom edge and the v_pos anchor for positive
                values, and the top edge and the v_pos anchor for negative
                values.

        """
        try:
            base_w, base_h = self.slide.surface.get_size()
            element_w, element_h = self.element_surface.get_size()
        except AttributeError:
            return

        # First figure out our anchor:

        if not h_pos:
            if x is not None:  # i.e. `if x:`
                h_pos = 'left'
            else:
                h_pos = 'center'

        if not v_pos:
            if y is not None:  # i.e. `if y:`
                v_pos = 'top'
            else:
                v_pos = 'center'

        # Next get the starting point for x, y based on that anchor

        if v_pos == 'top':
            calced_y = 0
        elif v_pos == 'bottom':
            calced_y = base_h - element_h
        elif v_pos == 'center' or v_pos == 'middle':
            calced_y = (base_h - element_h) / 2
        else:
            raise ValueError('Received invalid v_pos value:', v_pos)

        if h_pos == 'left':
            calced_x = 0
        elif h_pos == 'right':
            calced_x = base_w - element_w
        elif h_pos == 'center' or h_pos == 'middle':
            calced_x = (base_w - element_w) / 2
        else:
            raise ValueError("Received invalid 'h_pos' value:", h_pos)

        # Finally shift our x, y based on values passed.

        if x is not None:
            if -1.0 < x < 1.0:
                calced_x += x * base_w
            else:
                calced_x += x

        if y is not None:
            if -1.0 < y < 1.0:
                calced_y += y * base_h
            else:
                calced_y += y

        self.create_rect(int(calced_x), int(calced_y))
        self.show()

    def create_rect(self, x, y):
        """Uses the positional coordinates passed plus this element's surface
        size to create this element's rect attribute as it relates to the parent
        slide.

        Args:
            x: The x position of the upper left corner of this element.
            y: The y position of the upper left corner of this element.
        """
        self.rect = pygame.Rect((x, y), self.element_surface.get_size())

        # todo I would if rect should just be a property?

    def get_background(self, rect=None):
        """Returns the 'background' surface for this element which is freshly
        generated from all the lower layer elements that are active on this
        slide.

        Args:
            rect: Optional Pygame rect object which is the rect that will be
                used as the coordinates for the background surface. If this is
                not specified, this element's existing rect attribute is used.

        Returns:
            A pygame surface.
        """

        if not rect:
            rect = self.rect

        return self.slide.get_subsurface(rect, self.layer)

        # todo right now this always generates a new surface. Need to cache this
        # like track dirty rects or something so it can just return it as is if
        # nothing below it changed.

    def clear(self):
        """Clears the element off this slide and sets the surface to the a
        freshly-generated surface based on the lower layer elements on this
        slide."""
        self._opacity = 0

    def show(self):
        """Sets this element's surface so that it's built from this element,
        i.e. not including the background. This surface can then be blitted onto
        the existing slide."""
        self._opacity = 255

    def attach_decorator(self, decorator):
        """Attaches a decorator to this element.

        Args:
            decorator: The decorator object to attach
        """
        self.decorators.append(decorator)

    def remove_decorator(self, decorator):
        """Removes a decorator to this element.

        Args:
            decorator: The decorator object to remove
        """
        self.decorators.remove(decorator)

    def clear_decorators(self):
        """Removes all decorators from this element."""
        self.decorators = []

    def create_element_surface(self, width, height):
        """Creates the element_surface which will hold the 'foreground' content
        of this display element.

        Args:
            width: Width of the surface in pixels.
            height: Heigt of the surface in pixels.

        Classes based on this class will call this method after they determine
        the dimenions of the surface they'll need.

        This method also sets the proper palette (for 8-bit DMD surfaces) as
        well as adjusting foreground and background colors and shades.

        """
        self.element_surface = pygame.Surface((width, height),
                                              depth=self.slide.depth)

        if self.slide.depth == 8:
            self.element_surface.set_palette(
                self.slide.mpfdisplay.machine.display.dmd_palette)

    def adjust_colors(self, **kwargs):
        """Takes a settings dictionary and converts the object and background
        colors into a format Pygame can use.

        Args:
            **kwargs: A settings dictionary for this display element. Specific
                key / value pairs this method uses are shade, bg_shade, color,
                and bg_color.

        This method sets the adjusted_color and adjusted_bg_color attributes.

        """

        if self.slide.depth == 8:
            if 'shade' in kwargs:
                self.adjusted_color = (kwargs['shade'], 0, 0)
            else:
                self.adjusted_color = (15, 0, 0)  # todo default config

            if 'bg_shade' in kwargs:
                self.adjusted_bg_color = (kwargs['bg_shade'], 0, 0)
            else:
                self.adjusted_bg_color = None

        else:  # 24-bit
            if 'color' in kwargs:
                color_list = Config.hexstring_to_list(kwargs['color'])
                self.adjusted_color = (color_list[0], color_list[1],
                                       color_list[2])
            else:
                self.adjusted_color = (255, 255, 255)  # todo default config

            if 'bg_color' in kwargs:
                color_list = Config.hexstring_to_list(kwargs['color'])
                self.adjusted_bg_color = (color_list[0], color_list[1],
                                          color_list[2])
            else:
                self.adjusted_bg_color = None

    def adjust_color(self, color, transparent=False):
        if self.slide.depth == 8:
            if color:  # Non-black
                return ((color, 0, 0))

            elif transparent:
                return None

            else:  # Black
                return ((0, 0, 0))

        else:  # 24-bit
            if color:  # Non-black
                color_list = Config.hexstring_to_list(color)
                return ((color_list[0], color_list[1], color_list[2]))

            elif transparent:
                return None

            else:  # Black
                return ((0, 0, 0))

    def scrub(self):
        self.decorators = None
        self.rect = None
        self.slide = None
        self.element_surface = None

class Decorator(object):
    """Parent class of all Decorators."""

    def unload(self):
        """Removes this decorator from the parent element."""
        self.parent_element.decorators.remove(self)
        self.parent_element = None


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
