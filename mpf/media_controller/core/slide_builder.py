"""Contains the parent classes for MPF's display SlideBuilder class. """

# slide_builder.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import uuid

import mpf.media_controller.decorators
from mpf.system.timing import Timing


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
        self.log = logging.getLogger('SlideBuilder')
        self.machine = machine

        if self.machine.language:
            self.language = self.machine.language
        else:
            self.language = None

        # Tell the mode controller that it should look for SlidePlayer items in
        # modes.
        self.machine.modes.register_start_method(self.process_config,
                                                 'slideplayer')

    def process_config(self, config, mode=None, priority=0):
        self.log.debug("Processing SlideBuilder configuration. Base priority: "
                       "%s", priority)

        key_list = list()

        for event, settings in config.iteritems():
                settings = self.preprocess_settings(settings, priority)
                settings[0]['removal_key'] = mode
                # todo maybe a better way to add the removal key?

                key_list.append(self.machine.events.add_handler(
                                event,
                                self.build_slide,
                                settings=settings))

        return self.unload_slide_events, (key_list, mode)

    def unload_slide_events(self, removal_tuple):

        key_list, slide_key = removal_tuple

        self.log.debug("Removing SlideBuilder events")
        self.machine.events.remove_handlers_by_keys(key_list)

        if slide_key:
            self.machine.display.remove_slides(slide_key)

    def preprocess_settings(self, settings, base_priority=0):
        """Takes an unstructured list of SlidePlayer settings and processed them
        so they can be displayed.

        Args:
            settings: A list of dictionary of SlidePlayer settings for a slide.
            base_priority: An integer that will be added to slide's priority
                from the config settings.

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

        # This is a stupid band-aid because when modes load their slideplayer
        # settings are already processed. I don't know why though, but I don't
        # have time to track it down now. $50 to anyone who figures out why!!!

        # Settings can be a list of dicts or just a dict. (Preprocessing is what
        # turns a dict into a list, though I don't know how sometimes items are
        # getting the preprocessed entry in their dict but they're not a list???
        # todo

        if type(settings) is list and 'preprocessed' in settings[0]:
            return settings
        elif type(settings) is dict and 'preprocessed' in settings:
            return [settings]

        processed_settings = list()

        if type(settings) is dict:
            settings = [settings]

        last_settings = dict()
        first_settings = dict()

        # Drop this key into the settings so we know they've been preprocessed.
        first_settings['preprocessed'] = True

        for element in settings:

            # Create a slide name based on the event name if one isn't specified
            if 'slide_name' in element:
                first_settings['slide_name'] = element.pop('slide_name')

            if 'removal_key' in element:
                first_settings['removal_key'] = element.pop('removal_key')

            # If the config doesn't specify whether this slide should be made
            # active when this event is called, set a default value of True
            if 'slide_priority' in element:
                first_settings['slide_priority'] = (
                    element.pop('slide_priority') + base_priority)

            # If a 'clear_slide' setting isn't specified, set a default of True
            if 'clear_slide' in element:
                first_settings['clear_slide'] = element.pop('clear_slide')
            else:
                first_settings['clear_slide'] = True

            # If a 'persist_slide' setting isn't specified, set default of False
            if 'persist_slide' in element:
                first_settings['persist_slide'] = element.pop('persist_slide')
            else:
                first_settings['persist_slide'] = False

            if 'display' in element:
                first_settings['display'] = element.pop('display')

            if 'transition' in element:
                last_settings['transition'] = element.pop('transition')

            if 'name' not in element:
                element['name'] = None

            if 'expire' in element:
                first_settings['expire'] = Timing.string_to_ms(
                    element.pop('expire'))
            else:
                first_settings['expire'] = 0

            processed_settings.append(element)

        if 'slide_priority' not in first_settings:
            first_settings['slide_priority'] = base_priority

        if 'removal_key' not in first_settings:
            first_settings['removal_key'] = None

        # Now add back in the items that need to be in the first element
        processed_settings[0].update(first_settings)

        # And add the settings we need to the last entry
        processed_settings[-1].update(last_settings)

        return processed_settings

    def build_slide(self, settings, display=None, slide_name=None,
                    priority=None, **kwargs):
        """Builds a slide from a SlideBuilder set of keyword arguments.

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

        if 'preprocessed' not in settings[0]:
            settings = self.preprocess_settings(settings)

        if display:
            display = self.machine.display.displays[display]
        elif 'display' in settings[0]:
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

        # Does this slide need to auto clear itself?
        if 'expire' not in settings[0]:
            settings[0]['expire']

        # Does this slide name already exist for this display?

        if slide_name and slide_name in display.slides:  # Found existing slide
            slide = display.slides[slide_name]
            if 'clear_slide' in settings[0] and settings[0]['clear_slide']:
                slide.clear()
        else:  # Need to create a new slide
            # What priority?
            if priority is None:
                priority = settings[0]['slide_priority']

            slide = display.add_slide(name=slide_name, priority=priority,
                                      persist=settings[0]['persist_slide'],
                                      removal_key=settings[0]['removal_key'],
                                      expire_ms=settings[0]['expire'])

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
            settings['text'] = str(settings['text'])

            # Are there any text variables to replace on the fly?
            # todo should this go here?
            if '%' in settings['text']:
                # first check for player vars (%var_name%)
                if self.machine.player:
                    for name, value in self.machine.player:
                        if '%' + name + '%' in settings['text']:
                            settings['text'] = settings['text'].replace(
                                '%' + name + '%', str(value))

                # now check for single % which means event kwargs
                for kw in text_variables:
                    if '%' + kw in settings['text']:
                        settings['text'] = settings['text'].replace(
                            '%' + kw, str(text_variables[kw]))

        element_type = settings.pop('type').lower()

        element = slide.add_element(element_type, **settings)

        if 'decorators' in settings:

            if type(settings['decorators']) is dict:  # We have settings

                decorator_class = eval('mpf.media_controller.decorators.' +
                    settings['decorators']['type'] + '.' +
                    self.machine.display.decorators[
                    settings['decorators']['type']][1])

                element.attach_decorator(decorator_class(element,
                                                    **settings['decorators']))

            elif type(settings['decorators']) is list:

                for decorator in settings['decorators']:
                    decorator_class = eval('mpf.media_controller.decorators.' +
                        decorator['type'] + '.' +
                        self.machine.display.decorators[decorator['type']][1])

                element.attach_decorator(decorator_class(element, **decorator))


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
