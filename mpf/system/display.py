"""Contains the parent classes for MPF's display system, including the
DisplayController, MPFDisplay, DisplayElement, Slide, Transition, Decorator,
FontManager, and SlideBuilder."""

# display.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import uuid
import time
import os  # used for reading files. Might move this?

try:
    import pygame
    import pygame.locals

except:
    pass

from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing, Timer
from mpf.system.show_controller import ShowController
import mpf.display.transitions  # Really used even though Pyflakes says no


class DisplayController(object):
    """Parent class for the Display Controller in MPF. There is only one of
    these per machine. It's responsible for interacting with the display,
    regardless of what type it is (DMD, LCD, alphanumeric, etc.).

    Args:
        machine: The main MachineController object.

    Attributes:
        machine: The main MachineController object.
        hw_module: Reference to the active display hardware MPFDisplay instance.
        fonts: Reference to the Fon Module
        dmd_palette: An 8-bit Pygame palette MPF uses for the DMD.
        transitions: Dictionary of transitions available. Keys are the
            transition name, values are tuples of the transition's module and
            class.
        display_elements: Dictionary of registered display elements. Keys are
            the names of available display elements, values are the imported
            classes which new display elements of that type can subclass.
        displays: Dictionary of displays. Key is the display name, value is the
            associated MPFDisplay object.
        default_display: A reference to the default MPFDisplay object which is
            used if a display name is not specified.
        images: Dictionary of registered display images. Key is the string name
            for the image, value is the Pygame surface for this image.
        animations: Dictionary of registered animations. Key is the string name
            of the animation, value is a list of Pygame surfaces.

    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("DisplayController")
        self.log.debug("Loading the DisplayController")

        self.delay = DelayManager()

        self.hw_module = None
        self.fonts = None

        if 'Window' in self.machine.config:
            self.machine.events.add_handler('machine_init_phase2',
                                        self.machine.get_window, priority=1000)

        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_display_modules)
        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_display_elements)
        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_fonts)
        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_transitions)
        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_decorators)
        self.machine.events.add_handler('pygame_initialized',
                                        self._load_images)
        self.machine.events.add_handler('pygame_initialized',
                                        self._load_animations)
        self.machine.events.add_handler('machine_init_phase1',
                                        self._load_slidebuilder)

        self.machine.request_pygame()

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
        self.images = dict()
        self.animations = dict()

        # Register for events
        self.machine.events.add_handler('action_show_slide', self.show_slide)

    def _load_display_modules(self):
        # Load the display modules as specified in the config files

        # todo this could be cleaned up a bit

        self.machine.config['MPF']['display_modules']['modules'] = (
            self.machine.config['MPF']['display_modules']['modules'].split(' '))

        for module in self.machine.config['MPF']['display_modules']['modules']:
            i = __import__('mpf.display.modules.' + module.split('.')[0],
                           fromlist=[''])

            if i.is_used(self.machine.config):
                self.hw_module = getattr(i, module.split('.')[1])(self.machine)
                return  # we only support one type of hw_module at a time

    def _load_display_elements(self):
        self.display_elements = dict()

        self.machine.config['MPF']['display_modules']['elements'] = (
            self.machine.config['MPF']['display_modules']['elements'].split(' '))
        for element in self.machine.config['MPF']['display_modules']['elements']:
            i = __import__('mpf.display.elements.' + element.split('.')[0],
                           fromlist=[''])
            self.display_elements[element.split('.')[1]] = i

    def _load_fonts(self):
        if 'Fonts' not in self.machine.config:
            self.machine.config['Fonts'] = dict()

        self.fonts = FontManager(self.machine, self.machine.config['Fonts'])

    def _load_transitions(self):
        # This is tricky because we don't want to import them, rather, we just
        # want to list them.
        for k, v in (self.machine.config['MPF']['display_modules']
                     ['transitions'].iteritems()):
            __import__('mpf.display.transitions.' + v.split('.')[0])
            module = eval('mpf.display.transitions.' + v.split('.')[0])
            cls = v.split('.')[1]
            self.transitions[k] = (module, cls)

    def _load_decorators(self):
        # This is tricky because we don't want to import them, rather, we just
        # want to list them.
        for k, v in (self.machine.config['MPF']['display_modules']
                     ['decorators'].iteritems()):
            __import__('mpf.display.decorators.' + v.split('.')[0])
            module = eval('mpf.display.decorators.' + v.split('.')[0])
            cls = v.split('.')[1]
            self.decorators[k] = (module, cls)

    def _load_images(self):
        if 'Images' in self.machine.config:

            for image in self.machine.config['Images']:
                self.log.debug("Loading image: %s",
                               self.machine.config['Images'][image]['file'])
                if 'alpha_color' in self.machine.config['Images'][image]:
                    alpha_color = (self.machine.config['Images'][image]
                                   ['alpha_color'])
                else:
                    alpha_color = None

                if 'target' in self.machine.config['Images'][image]:
                    target = self.machine.config['Images'][image]['target']
                else:
                    target = None

                self.load_image(image,
                                self.machine.config['Images'][image]['file'],
                                alpha_color, target)

    def _load_animations(self):
        if 'Animations' in self.machine.config:
            for animation in self.machine.config['Animations']:

                if 'alpha_color' in self.machine.config['Animations'][animation]:
                    alpha_color = (self.machine.config['Animations'][animation]
                                   ['alpha_color'])
                else:
                    alpha_color = None

                self.load_animation(animation,
                    self.machine.config['Animations'][animation]['file'],
                    alpha_color)

    def _load_slidebuilder(self):

        self.slidebuilder = SlideBuilder(self.machine)

        if 'SlidePlayer' in self.machine.config:

            for event, settings in (self.machine.config['SlidePlayer'].
                                    iteritems()):
                settings = self.slidebuilder.preprocess_settings(settings)
                self.machine.events.add_handler(event,
                                                self.slidebuilder.build_slide,
                                                settings=settings)

    def set_default_display(self, display_name):
        """Sets the default display.

        Args:
            display_name: String name of the display you'd like to set to be the
                default.

        Returns: Nothing on success, False on failure.

        """

        if display_name in self.displays:
            self.default_display = self.displays[display_name]

        else:
            return False

    def load_image(self, name, file_name, alpha_color=None, target=None):
        """Loads an image from disk and makes it available as a registered
        image in the game.

        Args:
            name: A string of the name you'd like to refer to this image as in
                the game.
            file_name: The path and file name of where this file is coming
                from, based on the MPF root.
            alpha_color: An optional color that will be used as the alpha
                transparency index for this image.
        """

        # todo:
        # depth
        # w, h
        # load from image file

        file_name = self.locate_image_file(file_name)

        if not file_name:
            return False

        if file_name.endswith('.dmd'):
            image_surface = mpf.display.modules.dmd.load_dmd_file(
                file_name=file_name,
                palette=self.dmd_palette,
                alpha_color=alpha_color)
            self.images[name] = image_surface[0]

        elif file_name:  # we have a regular graphics file
            image_surface = pygame.image.load(file_name)

            if target == 'dmd':
                # This image will be shown on the DMD, so we need to convert its
                # surface to the DMD format
                image_surface = mpf.display.modules.dmd.surface_to_dmd(
                    surface=image_surface,
                    alpha_color=alpha_color)
                # todo add shades here if we ever support values other than 16

            self.images[name] = image_surface


    def load_animation(self, name, file_name, alpha_color=None):
        """Loads an animation from disk and makes it available as a registered
        animation in the game.

        Args:
            name: A string of the name you'd like to refer to this animation as
                in the game.
            file_name: The path and file name of where this file is coming
                from, based on the MPF root.
            alpha_color: An optional color that will be used as the alpha
                transparency index for this animation.
        """

        # todo:
        # depth
        # w, h
        # load from image file

        file_name = self.locate_animation_file(file_name)

        if not file_name:
            return False

        if file_name.endswith('.dmd'):
            surface_list = mpf.display.modules.dmd.load_dmd_file(file_name,
                self.dmd_palette, alpha_color)
        else:
            pass

        # todo add the alpha

        self.animations[name] = surface_list

    def add_image(self, name, surface):
        """Adds an image to the DisplayController.images library so it can be
        referenced by name later.

        Args:
            name: String name you want to refer to this image as.
            surface: Pygame surface which represents this image.

        This method saves the surface in memory, so your original object can be
        deleted. (Though Python's garbage collector won't actually destroy the
        surface since you have a reference to it here.)

        """
        self.images[name] = surface

    def add_animation(self, name, surface_list):
        """Adds an animation to the DisplayController.animations dictionary.

        Args:
            name: String name you want to refer to this animation as.
            surface_list: Python list of Pygame surfaces, one for each frame of
                the animation.

        """
        self.animations[name] = surface_list

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

    def locate_image_file(self, file_name):
        """Takes a file name and tries to find it on disk. First it
        checks the machine_folder images folder to see if there's a machine-
        specific image, then it tries the MPF system images folder.

        Args:
            file_name: String of the file name

        Returns: String of the full path (path + file name) of the image.
        """

        if not file_name:
            return

        full_path = os.path.join(self.machine.machine_path,
                                 self.machine.config['MPF']['paths']['images'],
                                 file_name)
        if os.path.isfile(full_path):
            return full_path
        else:
            full_path = os.path.join('mpf/images', file_name)
            if os.path.isfile(full_path):
                return full_path
            else:
                self.log.warning("Could not locate image file '%s'.", file_name)
                return None

    def locate_animation_file(self, file_name):
        """Takes a file name and tries to find it on disk. First it
        checks the machine_folder animations folder to see if there's a machine-
        specific animation, then it tries the MPF system animation folder.

        Args:
            file_name: String of the file name

        Returns: String of the full path (path + file name) of the animation.
        """

        # todo should probably combine all these locate file methods.

        if not file_name:
            return

        full_path = os.path.join(self.machine.machine_path,
                                 self.machine.config['MPF']['paths']['animations'],
                                 file_name)
        if os.path.isfile(full_path):
            return full_path
        else:
            full_path = os.path.join('mpf/animations', file_name)
            if os.path.isfile(full_path):
                return full_path
            else:
                self.log.warning("Could not locate animation file '%s'.",
                                 file_name)
                return None

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

        self.name = 'MPFDisplay'

        if not self.machine.display.default_display:
            self.machine.display.default_display = self

        self.machine.events.add_handler('pygame_initialized', self._initialize)

    def _initialize(self):
        # Internal method which initializes this display. This is separate from
        # __init__ because we have to wait until Pygame has been initialized

        # Create a default surface for this display
        self.surface = pygame.Surface((self.width, self.height),
                                      depth=self.depth)

        if self.depth == 8:
            self.surface.set_palette(self.palette)

        self.machine.display.displays[self.name] = self

        if not self.machine.display.default_display:
            self.machine.display.default_display = self

        self.current_slide = self.add_slide('default')

        self.machine.timing.add(
            Timer(self.update, frequency=1/float(self.config['fps'])))

    def add_slide(self, name, priority=0, persist=False):
        """Creates a new slide and adds it to the list of slides for this
        display.

        Args:
            name: String name of the new slide.
            priority: Relative priority of this slide versus others. Slides
                can only be shown if they are equal or higher priority than the
                priority of the display's current slide.
            presist: Boolean as to whether this slide should be saved when it
                is no longer being shown.

        Returns: Reference to the new slide object that was just created.

        """

        self.slides[name] = Slide(mpfdisplay=self, name=name, priority=priority,
                                  persist=persist, machine=self.machine)

        return self.slides[name]

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

        if new_slide.priority >= self.current_slide.priority:

            if transition:

                self.transition_dest_slide = new_slide
                transistion_class = eval('mpf.display.transitions.' + transition +
                                         '.' + self.transitions[transition][1])
                self.transition_slide = transistion_class(mpfdisplay=self,
                                                machine=self.machine,
                                                slide_a=self.current_slide,
                                                slide_b=self.transition_dest_slide,
                                                **kwargs)
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

    def set_current_slide(self, name=None, slide=None):
        """Tells the display to instantly set the current slide to the slide
        you pass.

        Args:
            name: The string name of the slide you want to make current.
            slide: The slide object you want to make current.

        Note: You only need to pass one parameter, either the slide name or the
        slide object itself. If you pass both, it will use teh slide object.

        If the new slide is not equal or higher priority than the current_slide,
        this method will do nothing.

        You can safely pass the existing current_slide which will have no effect.

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
        else:
            new_slide = self.slides[name]

        if new_slide is old_slide:
            return
        elif old_slide and new_slide.priority < old_slide.priority:
            return

        if old_slide and not old_slide.persist and old_slide in self.slides:
            # Not all slides are in self.slides, e.g. temp transition ones
            del self.slides[old_slide.name]

        self.current_slide = new_slide
        self.current_slide.active = True

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
    display elements include Text, Image, Shape, Animation, etc.

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

    """

    def __init__(self, slide):

        self.decorators = list()
        self.dirty = True
        self.rect = None
        self.slide = slide
        self._opacity = 255

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

        # todo right now this always generates a new image. Need to cache this
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
                color_list = ShowController.hexstring_to_list(kwargs['color'])
                self.adjusted_color = (color_list[0], color_list[1],
                                       color_list[2])
            else:
                self.adjusted_color = (255, 255, 255)  # todo default config

            if 'bg_color' in kwargs:
                color_list = ShowController.hexstring_to_list(kwargs['color'])
                self.adjusted_bg_color = (color_list[0], color_list[1],
                                          color_list[2])
            else:
                self.adjusted_bg_color = None


class Slide(object):
    """Parent class for a Slide object.

    MPF uses the concept of "slides" (think PowerPoint) as a collection of
    various display elements that should be shown on the display. There can be
    more than one slides defined at any given time, though only one is active
    at any given time. (Unless a transitioning is happening which transitions
    between an old slide and a new slide.

    Args:
        mpfdisplay: The display object this slide is for.
        name: String name of this slide.
        persist: Boolean as for whether this slide should be automatically
            destroyed once it's not shown on the display anymore.

    Attributes:
        name: The string name of this slide.
        elements: List of display elements that are active on this slide.
        surface: Reference to the Pygame surface this slide uses.
        priority: Integer of the relative priority of this slide. Lower
            priority slides won't be shown if a higher priority slide is
            currently active. (A slide of the same priority as the active slide
            can displace it.) Note that 'higher' numbers equal 'higher'
            priority, i.e. Priority 2 is higher than Priority 1.
        active: Boolean as to whether this slide is currently active. Active
            slides will constantly ensure that their display elements are
            refreshed, so this saves CPU cycles by not keeping non-active slides
            up-to-date.
        persist: Boolean as to whether this slide should persist when it becomes
            non-active. A value of False means that this slide will be destroyed
            as soon as it's no longer active.
        width: Width of this slide, in pixels.
        height: Height of this slide, in pixels.
        depth: Integer value of the color depth, either 8 or 24.
        palette: The Pygame palette this slide uses. (8-bit only)
    """

    def __init__(self, mpfdisplay, machine, name=None, priority=0,
                 persist=False):

        self.log = logging.getLogger('Slide')
        self.mpfdisplay = mpfdisplay
        self.machine = machine
        self.name = name

        self.priority = priority
        self.elements = list()

        # todo make priority a property with a setter that will show/hide the
        # slide if needed when it changes?

        self.width = mpfdisplay.width
        self.height = mpfdisplay.height
        self.depth = mpfdisplay.depth
        self.palette = mpfdisplay.palette

        if not name:
            self.name = str(uuid.uuid4())

        # create a Pygame surface for this slide based on the display's surface
        self.surface = pygame.Surface.copy(self.mpfdisplay.surface)

        self.active = False
        self.persist = False

    def update(self):
        """Updates this slide by calling each display element's update() method,
        and blits the results if there's an update.
        """

        for element in self.elements:
            if element.update():
                self.surface.blit(element.surface, element.rect)

    def get_subsurface(self, rect, layer=0):
        """Returns a surface of the slide based on the rect passed, but only for
        the elements of the passed layer and lower

        Args:
            rect: A pygame Rect object which defines the rectangle that will
                be returned.
            layer: Optional layer which defines the highest layer element
                that should be included in the surface.

        Returns: A Pygame surface.

        """

        surface = pygame.Surface(rect.size, depth=self.depth)
        surface.set_palette(self.palette)

        for element in self.elements:
            if element.layer >= layer:
                break
            surface.blit(element.surface, (0, 0), area=rect)

        return surface

    def blit_8bit_alpha(self, source_surface, dest_surface, x, y):
        """Blits an 8-bit surface onto another using the DMD-style alpha values.

        Args:
            source_surface: Source 8-bit pygame surface
            dest_surface: Destination 8-bit Pygame surface the source surface
                will be blitted *to*.
            x: x position of the upper left corner of where the source surface
                will be blitted to on the destination surface.
            y: y position (goes with `x` above)

        Note this blit is expensive, so it's only used when it's specifically
        called for.
        """

        working_surface = dest_surface.subsurface((x, y,
                                                   source_surface.get_width(),
                                                   source_surface.get_height()))

        dest_pa = pygame.PixelArray(working_surface)
        source_pa = pygame.PixelArray(source_surface)

        for y in range(len(working_surface.get_height())):
            for x in range(len(working_surface.get_width())):

                # This blend formula is complex, so here's how it was worked out

                # alpha_percet = (source_pa[x, y] >> 4) / 15.0
                # delta = source_pa[x, y] - dest_pa[x, y]
                # change = delta * alpha_percent
                # new_value = dest_pa[x, y] + change
                # dest_pa[x, y] = new_value

                # now here they all are on one line

                dest_pa[x, y] = (dest_pa[x, y] +
                                 ((source_pa[x, y] - dest_pa[x, y]) *
                                  (source_pa[x, y] >> 4) / 15.0))

    def add_element(self, element_type, name=None, x=None, y=None, h_pos=None,
                    v_pos=None, **kwargs):
        """Adds a display element to the slide.

        Args:
            element_type: String name of the type of element you're adding.
                (i.e. 'Text', 'Image', 'Shape', etc.).
            name: Friendly name of the new element.
            x: 'x' position of the upper left corner of this element. This is
                either the 'x' position, or an offset in pixels, or an offset
                percentage. See the documentation for the calc_position method
                for details.
            y: 'y' position or offset, like x above.
            h_pos: Relative horizontal position: left, center, or right.
            v_pos: Relative verical position: top, center, or bottom.
            **kwargs: A list of key/value settings for the element you're
                adding.

        Returns:
            An element dictionary, which includes:
            name: String name of the element.
            element: The newly-created display element object.
            layer: Integer of the relative layer of this element on the
                slide.
            x: x position of the upper left corner of this element on the slide.
            y: y position of the upper left corner of this element on the slide.
        """

        self.log.debug("Adding %s element to slide %s.%s", element_type,
                       self.mpfdisplay.name, self.name)

        element = getattr(self.machine.display.display_elements[
            element_type], element_type)(slide=self,
                                         machine=self.machine,
                                         x=x,
                                         y=y,
                                         h_pos=h_pos,
                                         v_pos=v_pos,
                                         **kwargs)

        self.elements.append(element)

        # Sort the list by layer, lowest to highest. This ensures that when
        # it's rendered, the lower layer elements are rendered first and
        # therefore "under" the higher layer elements
        self.elements.sort(key=lambda x: int(x.layer))

        #self.dirty = True

        return element

    def clear(self):
        """Removes all elements from the slide and resets the slide to all
        black."""
        self.elements = list()
        self.surface.fill((0, 0, 0))
        self.dirty = True

    def show(self):
        """Shows this slide by making it active.

        This is immediate. If you want a transition, use the
        MPFDisplay.transition() method.

        This method will only show the slide if its priority is the same or
        higher than the existing slide.
        """


        if self.mpfdisplay.current_slide and (
                self.mpfdisplay.current_slide.priority <= self.priority):

            self.log.debug('Showing slide: %s', self.name)
            self.active = True
            self.mpfdisplay.set_current_slide(slide=self)


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
        self.duration = Timing.string_to_secs(duration)

        # Need to make sure both the slides have rendered in case they're new
        self.slide_b.update()
        self.slide_a.update()

        self.start_time = time.time()
        self.end_time = self.start_time + self.duration

        # mark both slides as active
        self.slide_a.active = True
        self.slide_b.active = True

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
                                 self.machine.config['MPF']['paths']['fonts'],
                                 file_name)
        if os.path.isfile(full_path):
            return full_path
        else:
            full_path = os.path.join('mpf/fonts', file_name)
            if os.path.isfile(full_path):
                return full_path
            else:
                self.log.warning("Could not locate font file '%'. Default font"
                                 "will be used instead.")


class SlideBuilder(object):
    """Parent class for SlideBuilder objects which are things you configure via
    the machine config files that let you display text messages based on game
    events. You can use this to show game status, players, scores, etc. Any
    setting that is available via the text method of the display controller is
    available here, including positioning, fonts, size, delays, etc.

    Args:
        machine: The main machine object.

    """

    def __init__(self, machine):
        self.log = logging.getLogger('SlidePlayer')
        self.machine = machine

        if 'SlidePlayer' in self.machine.config:
            self.config = self.machine.config['SlidePlayer']
        else:
            self.config = dict()

        if self.machine.language:
            self.language = self.machine.language
        else:
            self.language = None

        # Set up the event registrations for each entry

    def preprocess_settings(self, settings):
        """Takes an unstructured list of SlidePlayer settings and processed them
        so they can be displayed.

        Args:
            settings: A list of dictionary of SlidePlayer settings for a slide.

        Returns: A python list with all the settings in the right places.

        This method does a bunch of things, like making sure all the needed
        values are there, and moving certain things to the first and last
        elements when there are multiple elements used on one slide. (For
        example, if one of the elements wants to clear the slide, it has to
        happen first. If there's a transition, it has to happen last after the
        slide is built, etc.

        The returned settings list can be safely called with the by display()
        with the preprocessed=True flag.

        """

        processed_settings = list()

        if type(settings) is dict:
            settings = [settings]

        last_settings = dict()
        first_settings = dict()

        # Drop this key into the settings so we know they've been preprocessed.
        first_settings['preprossed'] = True

        for element in settings:

            # Create a slide name based on the event name if one isn't specified
            if 'slide_name' in element:
                first_settings['slide_name'] = element.pop('slide_name')

            # If the config doesn't specify whether this slide should be made
            # active when this event is called, set a default value of True
            if 'slide_priority' in element:
                first_settings['slide_priority'] = element.pop('slide_priority')

            # If a 'clear_slide' setting isn't specified, set a default of True
            if 'clear_slide' in element:
                first_settings['clear_slide'] = element.pop('clear_slide')

            # If a 'persist_slide' setting isn't specified, set default of False
            if 'persist_slide' in element:
                first_settings['persist_slide'] = element.pop('persist_slide')

            if 'display' in element:
                first_settings['display'] = element.pop('display')

            if 'transition' in element:
                last_settings['transition'] = element.pop('transition')

            processed_settings.append(element)

        # Now add back in the items that need to be in the first element
        processed_settings[0].update(first_settings)

        # And add the settings we need to the last entry
        processed_settings[-1].update(last_settings)

        return processed_settings

    def build_slide(self, settings, display=None, slide_name=None,
                    priority=None, **kwargs):
        """Buils a slide from a SlideBuilder set of keyword arguments.

        Args:
            settings: Python dictionary of settings for this slide. This
                includes settings for the various Display Elements as well as
                any transition.
            display: String name of the display this slide is being built for.
            slide_name: String name of the slide that's being built. If this
                slide exists, the elements here will be added to that slide. If
                it doesn't exist, a new slide will be created. If no slide name
                is passed, a new slide will be created and given a UUID4 name.
            priority: Integer of the priority of this slide.
            **kwargs: Catch all since this method is often registered as a
                callback for events which means there could be random event
                keyword argument pairs attached.

        Returns: Slide object from the slide it built (whether or not it's
            showing now).

        """

        if not 'preprocessed' in settings:
            settings = self.preprocess_settings(settings)

        if display:
            display = self.machine.display.displays[display]
        elif 'display' in settings:
            display = settings[0]['display']
            display = self.machine.display.displays[display]
        else:
            display = self.machine.display.default_display



        # Figure out which slide we're dealing with
        if not slide_name:
            if 'slide_name' in settings[0]:
                slide_name = settings[0]['slide_name']
            else:
                slide_name = str(uuid.uuid4())

        # Does this slide name already exist for this display?
        if slide_name in display.slides:  # Found existing slide
            slide = display.slides[slide_name]
            if settings[0]['clear_slide']:
                slide.clear()
        else:  # Need to create a new slide

            # What priority?
            if priority is None:
                if 'slide_priority' in settings[0]:
                    priority = settings[0]['slide_priority']
                else:
                    priority = 0

            slide = display.add_slide(name=slide_name, priority=priority)

        # loop through and add the elements
        for element in settings:
            self._add_element(slide, text_variables=kwargs, **element)

        # do the transition
        if 'transition' in settings[-1]:
            if type(settings[-1]['transition']) is dict:  # We have settings
                slide = display.transition(new_slide=slide,
                                           transition=settings[-1]
                                           ['transition']['type'],
                                           **settings[-1]['transition'])
            else:  # no transition settings, just use defaults
                slide = display.transition(new_slide=slide,
                                           transition=settings[-1]
                                           ['transition'])
            slide.show()

        else:
            slide.show()

        return slide

    def _add_element(self, slide, text_variables, **settings):
        # Internal method which actually adds the element to the slide

        # Process any text
        if 'text' in settings:

            # Are there any variables to replace on the fly?
            if '%' in settings['text']:

                # first check for player vars
                if self.machine.game and self.machine.game.player:
                    for var in self.machine.game.player.vars:
                        if '%' + var + '%' in settings['text']:
                            settings['text'] = settings['text'].replace(
                                '%' + var + '%',
                                str(self.machine.game.player.vars[var]))

                # now check for single % which means event kwargs
                for kw in text_variables:
                    if '%' + kw in settings['text']:
                        settings['text'] = settings['text'].replace(
                            '%' + kw, str(text_variables[kw]))
        element_type = settings.pop('type')

        element = slide.add_element(element_type, **settings)

        if 'decorators' in settings:



            if type(settings['decorators']) is dict:  # We have settings

                decorator_class = eval('mpf.display.decorators.' +
                    settings['decorators']['type'] + '.' +
                    self.machine.display.decorators[
                    settings['decorators']['type']][1])

                element.attach_decorator(decorator_class(element,
                                                    **settings['decorators']))

            elif type(settings['decorators']) is list:

                for decorator in settings['decorators']:
                    decorator_class = eval('mpf.display.decorators.' +
                    decorator['type'] + '.' +
                    self.machine.display.decorators[decorator['type']][1])

                element.attach_decorator(decorator_class(element, **decorator))


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
