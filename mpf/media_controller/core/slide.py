"""Contains the Slide parent class."""

# display.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import uuid

from mpf.system.timing import Timing

try:
    import pygame
except:
    pass


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
        expire_ms: How many ms this slide should live for. Default is 0 which
            means it will not automatically be removed.
        mode: A reference to the Mode which created this slide.

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
        expire_ms: Integer of ms that will cause this slide to automatically
            remove itself. The timer doesn't start until the slide is shown.

    """
    def __init__(self, mpfdisplay, machine, priority=0, persist=False,
                 expire_ms=0, mode=None, name=None):

        self.log = logging.getLogger('Slide')

        self.mpfdisplay = mpfdisplay
        self.machine = machine
        self.priority = priority
        self.persist = persist
        self.expire_ms = expire_ms
        self.mode = mode
        self.name = name
        self.active_transition = False
        self.removal_delay = None
        self.creation_tick = self.machine.tick_num

        self.elements = list()
        self.pending_elements = set()
        """Elements which have related assets that are still loading in a
        background thread."""

        self.ready_callbacks = list()
        """List of callback/kwarg tuples which will be called when all the
        elements of this slide are ready to be shown."""

        # todo make priority a property with a setter that will show/hide the
        # slide if needed when it changes?

        self.width = mpfdisplay.width
        self.height = mpfdisplay.height
        self.depth = mpfdisplay.depth
        self.palette = mpfdisplay.palette

        # create a Pygame surface for this slide based on the display's surface
        self.surface = pygame.Surface.copy(self.mpfdisplay.surface)

        if self.expire_ms:
            self.schedule_removal()

    def tickle(self):
        self.creation_tick = self.machine.tick_num
        self.mpfdisplay.refresh()

    def ready(self):
        if not self.pending_elements:
            self.log.debug("Checking if slide is ready... Yes!")
            return True
        else:
            self.log.debug("Checking if slide is ready... No!")
            return False

    def add_ready_callback(self, callback, **kwargs):
        self.log.debug("Adding a ready callback: %s, %s", callback, kwargs)
        for c, _ in self.ready_callbacks:
            if c == callback:
                return False

        self.ready_callbacks.append((callback, kwargs))
        return True

    def _process_ready_callbacks(self):
        self.log.debug("Slide is now ready. Processing ready_callbacks... %s",
                       self.ready_callbacks)
        for callback, kwargs in self.ready_callbacks:
            callback(**kwargs)

        self.ready_callbacks = list()

    def update(self):
        """Updates this slide by calling each display element's update() method,
        and blits the results if there's an update.
        """
        if self.pending_elements:
            return

        force_dirty = False

        if self not in self.mpfdisplay.slides:
            return

        for element in self.elements:

            if element.update():
                self.surface.blit(element.surface, element.rect)
                force_dirty = True
            elif force_dirty:
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
        if surface.get_bytesize() == 1:
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

        del dest_pa
        del source_pa

    def add_element(self, element_type, name=None, x=None, y=None, h_pos=None,
                    v_pos=None, text_variables=None, **kwargs):
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
            v_pos: Relative vertical position: top, center, or bottom.
            **kwargs: A list of key/value settings for the element you're
                adding.

        Returns:
            An element dictionary, which includes:
                name: String name of the element.
                element: The newly-created display element object.
                layer: Integer of the relative layer of this element on the
                    slide.
                x: x position of the upper left corner of this element on the
                    slide.
                y: y position of the upper left corner of this element on the
                    slide.

        """
        element_type = element_type.lower()

        try:
            name = name.lower()
        except AttributeError:
            pass

        element_class = (self.machine.display.display_elements[element_type].
                         display_element_class)

        element = element_class(slide=self,
                                machine=self.machine,
                                x=x,
                                y=y,
                                h_pos=h_pos,
                                v_pos=v_pos,
                                name=name,
                                text_variables=text_variables,
                                **kwargs)

        if not element.ready:
            self.log.debug("Element is not ready. Adding to pending elements "
                           "list. %s", element)
            self.pending_elements.add(element)
            element.notify_when_loaded.add(self._element_asset_loaded)

        self.elements.append(element)

        # Sort the list by layer, lowest to highest. This ensures that when
        # it's rendered, the lower layer elements are rendered first and
        # therefore "under" the higher layer elements
        self.elements.sort(key=lambda i: int(i.layer))

        return element

    def _element_asset_loaded(self, element):
        self.log.debug("_element_asset_loaded")
        self.pending_elements.discard(element)

        if not self.pending_elements:
            self._process_ready_callbacks()

    def remove_element(self, name):
        """Removes a display element from the slide.

        Args:
            name: String name of the display element you want to remove.
        """

        mark_dirty = False

        # Reverse so we can mark any elements below this as dirty
        for element in reversed(self.elements):
            if element.name == name:
                self.elements.remove(element)
                mark_dirty = True
            elif mark_dirty:
                element.dirty = True

        # If we wanted to optimize more, we could only mark the Rect of the
        # element that was removed as dirty, but meh. If we do that we should
        # probably instead create some kind of dirty rect handler since we
        # could use it in other places too.

    def clear(self):
        """Removes all elements from the slide and resets the slide to all
        black."""
        self.elements = list()
        self.surface = pygame.Surface.copy(self.mpfdisplay.surface)
        self.dirty = True

    def refresh(self, force_dirty=False):
        """Refreshes the slide by clearing it, and updating all the display
        elements.

        Args:
            force_dirty: Boolean which controls whether you want to force all
                the elements to be marked as dirty so they're regenerated.

        """
        self.surface = pygame.Surface.copy(self.mpfdisplay.surface)

        if force_dirty:
            for element in self.elements:
                element.dirty = True
        self.update()

    def schedule_removal(self, removal_time=None):
        """Schedules this slide to automatically be removed.

        Args:
            removal_time: MPF time string of when this slide should be removed.
                If no time is specified, the slide's existing removal time is
                used. If the slide has no existing time, the slide will not be
                removed.
        """
        if removal_time:
            self.expire_ms = Timing.string_to_ms(removal_time)

        if self.expire_ms:
            self.active_delay = self.machine.delay.add(ms=self.expire_ms,
                                                       callback=self.remove)

    def remove(self, refresh_display=True):
        """Removes the slide.

        Args:
            refresh_display: Boolean if you want the display to refresh itself
                based on changes that occurred due to this slide removal.
                Default is True, but if you're looping through and removing a
                bunch of slides, you can use False and then manually call it
                once when you're done.

        This method will scrub the elements which will remove and shut them
        down, remove any active delays, and remove this slide from the display
        slides list.

        """
        for element in self.elements:
            element.scrub()

        self.elements = list()
        self.pending_elements = None
        self.ready_callbacks = None
        self.persist = False
        self.active_transition = False
        self.surface = None

        if self.removal_delay:
            self.machine.delay.remove(self.removal_delay)

        try:
            self.mpfdisplay.slides.remove(self)
        except ValueError:
            pass

        self.mpfdisplay.refresh()

        # todo where is this used? Should we force removal?


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
