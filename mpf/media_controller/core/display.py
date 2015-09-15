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

except:
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
        self.slidebuilder = SlideBuilder(self.machine)

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
        self.machine.events.add_handler('action_show_slide', self.show_slide)

        if 'slide_player' in self.machine.config:
            self.machine.events.add_handler('pygame_initialized',
                self._load_slidebuilder_config)

    def _load_slidebuilder_config(self):
        # This has to be a separate method since slidebuilder.process config
        # returns an unloader method so we can't use it as an event handler
        self.slidebuilder.process_config(
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

    def show_slide(self, slide, display=None, **kwargs):
        """ Shows a slide. This method assumes the slide exists for this display
        already.

        Args:
            slide: The Slide object you want to show.
            display: The name of the display you'd like to show this slide on.
            **kwargs: Optional dictionary of settings which could add a
                transition. See the documentation on the SlideBuilder for all
                the options.
        """

        # figure out which display we're dealing with
        if not display:
            display = self.default_display
        else:
            display = self.displays[display]

        if 'transition' in kwargs:
            transition_settings = kwargs['transition']
            transition_type = kwargs['transition'].pop('type')

            display.transition(new_slide=display.slides[slide],
                               transition=transition_type,
                               **transition_settings)

    def remove_slides(self, removal_key):

        for display_obj in self.displays.values():
            display_obj.remove_slides_by_key(removal_key)


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

        self.slides = dict()
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

        self.current_slide = self.add_slide(name='blank', persist=True)

        self.machine.timing.add(
            Timer(self.update, frequency=1/float(self.config['fps'])))

    def add_slide(self, name, priority=0, persist=False, removal_key=None,
                  expire_ms=0, mode=None):
        """Creates a new slide and adds it to the list of slides for this
        display.

        Args:
            name: String name of the new slide.
            priority: Relative priority of this slide versus others. Slides
                can only be shown if they are equal or higher priority than the
                priority of the display's current slide.
            presist: Boolean as to whether this slide should be saved when it
                is no longer being shown.
            removal_key: Unique identifier that can be used later to remove this
                slide.
            expire_ms: Integer of ms that will cause this slide to automatically
                remove itself. The timer doesn't start until the slide is shown.
            mode: A reference to the Mode which created this slide

        Returns: Reference to the new slide object that was just created.

        """
        self.slides[name] = Slide(mpfdisplay=self, name=name, priority=priority,
                                  persist=persist, machine=self.machine,
                                  removal_key=removal_key,
                                  expire_ms=expire_ms,
                                  mode=mode)

        return self.slides[name]

    def remove_slides_by_key(self, removal_key):
        """Removes any slides with the removal key passed.

        Args:
            removal_key: Key for the slides you want to remove.

        Removing an active slide will automatically cause the next highest
        priority slide to be shown.

        You can safely call this method even if the removal key doesn't match
        any slides.
        """

        self.log.debug("Removing slides by key: %s", removal_key)

        if removal_key:
            for slide_obj in self.slides.values():
                if slide_obj.removal_key == removal_key:
                    slide_obj.remove()

    def transition(self, new_slide, transition=None, **kwargs):
        """Transitions this display to a new slide.

        Args:
            new_slide: Reference to the Slide object you'd like to transition
                to.
            tranisition: String name of the transition type you'd like to use.
                Note if this is `None`, it just switches to the new slide
                instantly. (i.e. No transition.)
            **kwargs: Optional key/value pairs which control settings for the
                transition. See the documentation for each transition type, as
                there are lots of different settings and they're all different
                depending on the type of transition.

        Returns: A reference to the new slide this display will use. If the
            new_slide passed is lower than the priority of the current_slide,
            then this transition won't happen and the display will continue to
            show the current slide. If no transition is specified, this method
            returns a reference to the new_slide. And if there will be a
            transition, this method will return a reference to the temporary
            slide which the transition uses to actually perform the transition.
        """

        if not new_slide.ready():

            kwargs['transition'] = transition
            new_slide.add_ready_callback(self.transition, new_slide=new_slide,
                                         **kwargs)
            return self.current_slide

        if new_slide.priority >= self.current_slide.priority:

            if transition:

                self.transition_dest_slide = new_slide

                transition_class = eval('mpf.media_controller.transitions.' +
                                        transition + '.' +
                                        self.transitions[transition][1])
                self.transition_slide = (
                    transition_class(mpfdisplay=self,
                                     machine=self.machine,
                                     slide_a=self.current_slide,
                                     slide_b=self.transition_dest_slide,
                                     **kwargs))
                self.flag_active_transition = True

                return self.transition_slide

            else:
                return new_slide

        else:
            return self.current_slide

    def transition_complete(self):
        """Tells the display that the current transition is complete and
        swithces the display over to the destination slide.

        This method is automatically called when a transition ends. It can
        safely be called during a transition to end it early.

        """
        self.flag_active_transition = False
        self.set_current_slide(slide=self.transition_dest_slide)
        self.transition_object = None

    def set_current_slide(self, name=None, slide=None, force=False):
        """Tells the display to instantly set the current slide to the slide
        you pass.

        Args:
            name: The string name of the slide you want to make current.
            slide: The slide object you want to make current.
            force: Boolean to force the slide you're passing to show even if
                it's a lower priority than what's currently showing. In general
                you shouldn't use this. It only exists so MPF can cleanly remove
                higher priority slides if they're killed while active.

        Note: You only need to pass one parameter, either the slide name or the
        slide object itself. If you pass both, it will use teh slide object.

        If the new slide is not equal or higher priority than the current_slide,
        this method will do nothing.

        You can safely pass the existing current_slide which will have no
        effect.

        This method will destroy the old slide unless that slide's `persist`
        attribute is True.

        If you want to show the new slide with a transition, use the
        'transition()' method instead of this method.

        """

        old_slide = None

        if self.current_slide:
            old_slide = self.current_slide
            old_slide.active = False

        if slide:
            new_slide = slide
        elif name and name in self.slides:
            new_slide = self.slides[name]
        else:
            if 'blank' in self.slides:
                new_slide = self.slides['blank']
            else:
                new_slide = self.add_slide(name='blank', persist=True)

        self.log.debug('Setting current slide to: %s', new_slide.name)

        if new_slide is old_slide:
            return
        elif (not force and old_slide and
                new_slide.priority < old_slide.priority):
            self.log.debug('New slide has a lower priority (%s) than the '
                           'existing slide (%s). Not showing new slide.',
                           new_slide.priority, old_slide.priority)
            return

        if not new_slide.ready():
            new_slide.add_ready_callback(self.set_current_slide,
                                         slide=new_slide)
        else:
            self.current_slide = new_slide
            self.current_slide.update()
            self.current_slide.active = True
            new_slide.schedule_removal()

        # We will delete the existing (old slide) if:
        # - it's not set to persist
        # - the new slide doesn't expire (meaning we need the old slide)
        # - we have a record of the old slide
        # - it's not the last slide in a mode (so we have something to show if
        #   this mode ends)
        if (    old_slide and
                not old_slide.persist and
                not new_slide.expire_ms and
                old_slide.name in self.slides and
                not self.is_only_slide_from_mode(old_slide)):
            # Not all slides are in self.slides, e.g. temp transition ones

            del self.slides[old_slide.name]

    def is_only_slide_from_mode(self, slide):
        """Checks to see if the slide passed is the only slide in a mode.

        Args:
            slide: A Slide object

        Returns True if this is the only slide in a mode, False if there are
        other slides from that mode.

        """

        slides = [self.slides[x].mode for x in self.slides]

        if slides.count(self.slides[x].mode) == 1:
            return True
        else:
            return False

    def show_current_active_slide(self):
        self.set_current_slide(slide=self.get_highest_priority_slide(),
                               force=True)


    def get_highest_priority_slide(self):

        max_value = 0
        current_slide = None

        for _, slide_obj in self.slides.iteritems():
            if slide_obj.priority >= max_value:
                max_value = slide_obj.priority
                current_slide = slide_obj

        return current_slide

    def update(self):
        """Updates the contents of the current slide. This method can safely
        be called frequently.
        """
        self.current_slide.update()

    def get_surface(self):
        """Returns the surface of the current slide."""
        return self.current_slide.surface

    def clear(self):
        """Clears (blanks) the display."""

        self.log.debug("Clearing the display")
        self.set_current_slide(name='blank', force=True)


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

        base_w, base_h = self.slide.surface.get_size()
        element_w, element_h = self.element_surface.get_size()

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

    def scrub(self):
        pass


class Transition(Slide):
    """Parent class for all slide Transition objects. Subclasses Slide.

    Args:
        mpfdisplay: The MPFDisplay object this transition is for.
        machine: The main MachineController object.
        slide_a: The current (outgoing) Slide.
        slide_b: The new (incoming) Slide.
        duration: MPF timing string for how long this transition will take.
            Default is 1 second.
        **kwargs: Any additional key/value settings for this transition. (All
            transitions are different and have different settings.)

    Attributes:
        slide_a: Outgoing slide.
        slide_b: Incomding slide.
        duration: Duration in seconds (float or int).
        start_time: Real world time when this transition began.
        end_time: Real world time when this transition will complete.
    """

    def __init__(self, mpfdisplay, machine, slide_a, slide_b, duration='1s',
                 **kwargs):

        super(Transition, self).__init__(mpfdisplay, machine, name=self.name)

        self.slide_a = slide_a
        self.slide_b = slide_b
        self.priority = slide_b.priority
        self.duration = Timing.string_to_secs(duration)

        # Need to make sure both the slides have rendered in case they're new
        self.slide_b.update()
        self.slide_a.update()

        self.start_time = time.time()
        self.end_time = self.start_time + self.duration

        # mark both slides as active
        self.slide_a.active = True
        self.slide_b.active = True

        # todo if an element is not loaded on the B slide when this transition
        # is called, it will crash. Need to probably not call transition
        # directly and switch to some kind of loader method for it that can
        # delay this as needed.

    def update(self):
        """Called to update the slide with the latest transition animation.

        Completely replaces the update() method in the parent class since the
        transition class is a special type of slide.
        """

        # Update the slides (so animations keep playing during the transition)
        self.slide_a.update()
        self.slide_b.update()

        # figure out what percentage along we are
        self.percent = (time.time() - self.start_time) / self.duration

        if self.percent >= 1.0:
            self.complete()

        if self.active:
            self.mpfdisplay.dirty = True

        # don't set self._dirty since this transition slide is always dirty as
        # long as it's active

    def complete(self):
        """Mark this transition as complete."""
        # this transition is done
        self.slide_a.active = False
        self.mpfdisplay.transition_complete()


class Decorator(object):
    """Parent class of all Decorators."""

    def unload(self):
        """Removes this decorator from the parent element."""
        self.parent_element.decorators.remove(self)


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
