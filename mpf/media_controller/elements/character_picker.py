"""Contains the parent class of the CharacterPicker DisplayElement"""

# character_picker.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from collections import deque
from copy import deepcopy
from mpf.media_controller.core.display import DisplayElement
from mpf.system.timing import Timing
import pygame


class CharacterPicker(DisplayElement):
    """Represents an character picker display element.

    Args:
        slide: The Slide object this animation is being added to.
        machine: The main machine object.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at: https://missionpinball.com/docs/displays/display-elements/positioning/

    """

    def __init__(self, slide, machine, x=None, y=None, h_pos=None,
                     v_pos=None, layer=0, **kwargs):

        super(CharacterPicker, self).__init__(slide, x, y, h_pos, v_pos, layer)

        self.fonts = machine.display.fonts
        self.slide = slide
        self.machine = machine
        self.layer = layer
        self.config = deepcopy(kwargs)
        self.char_list = deque()
        self.cursor_position = 0
        self.selected_char = ''
        self.registered_event_handlers = list()

        if 'selected_char_color' not in self.config:
            self.config['selected_char_color'] = 0

        if 'selected_char_bg' not in self.config:
            self.config['selected_char_bg'] = 15

        if 'char_width' not in self.config:
            self.config['char_width'] = 11

        if 'width' not in self.config:
            self.config['width'] = None

        if 'height' not in self.config:
            self.config['height'] = 15

        if 'char_x_offset' not in self.config:
            self.config['char_x_offset'] = 0

        if 'char_y_offset' not in self.config:
            self.config['char_y_offset'] = 0

        if 'shift_left_tag' not in self.config:
            self.config['shift_left_tag'] = 'left_flipper'

        if 'shift_right_tag' not in self.config:
            self.config['shift_right_tag'] = 'right_flipper'

        if 'select_tag' not in self.config:
            self.config['select_tag'] = 'start'

        if 'name' in self.config:
            self.name = self.config['name']
        else:
            self.name = 'character_picker'

        if 'char_list' not in self.config:
            self.config['char_list'] = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        if 'max_chars' not in self.config:
            self.config['max_chars'] = 3

        if 'timeout' not in self.config:
            self.config['timeout'] = None
        else:
            self.config['timeout'] = (
                Timing.string_to_secs(self.config['timeout']))

        if 'back_char' not in self.config:
            self.config['back_char'] = 'back_arrow_7x7'

        if 'end_char' not in self.config:
            self.config['end_char'] = 'end_11x7'

        if 'back_char_selected' not in self.config:
            self.config['back_char_selected'] = 'back_arrow_7x7_selected'

        if 'end_char_selected' not in self.config:
            self.config['end_char_selected'] = 'end_11x7_selected'

        if 'image_padding' not in self.config:
            self.config['image_padding'] = 1

        if 'return_param' not in self.config:
            self.config['return_param'] = 'award'

        self.config['selected_char_color'] = (
            self.adjust_color(self.config['selected_char_color']))
        self.config['selected_char_bg'] = (
            self.adjust_color(self.config['selected_char_bg']))

        self.adjust_colors(**self.config)

        self.config['color'] = self.adjusted_color
        self.config['bg_color'] = self.adjusted_bg_color

        self.char_list.extend(self.config['char_list'])
        self.char_list.append('back')
        self.char_list.append('end')
        self.char_list.rotate(len(self.char_list)/2)

        self.cursor_position = len(self.char_list)/2
        self.selected_char = self.char_list[self.cursor_position]

        self.machine._set_machine_var(name=self.name + '_chars_entered',
                                      value='')

        self.setup_switch_handlers()

        self.render()

    def setup_switch_handlers(self):

        self.registered_event_handlers.append(self.machine.events.add_handler(
            'switch_' + self.config['shift_left_tag'] + '_active',
            self.shift, places=1))
        self.registered_event_handlers.append(self.machine.events.add_handler(
            'switch_' + self.config['shift_right_tag'] + '_active',
            self.shift, places=-1))
        self.registered_event_handlers.append(self.machine.events.add_handler(
            'switch_' + self.config['select_tag'] + '_active',
            self.select))

    def shift(self, places=1):

        if places > 0:
            self.machine.events.post(self.name + '_shift_left')
        else:
            self.machine.events.post(self.name + '_shift_right')

        self.char_list.rotate(places)
        self.selected_char = self.char_list[self.cursor_position]
        self.render()

    def select(self):
        if self.selected_char == 'back':
            self.machine._set_machine_var(name=self.name + '_chars_entered',
            value=self.machine.machine_vars[self.name + '_chars_entered'][:-1])
            self.machine.events.post(self.name + '_select_back')
        elif self.selected_char == 'end':
                self.machine.events.post(self.name + '_select_end')
                self.complete()
        else:
            self.machine.events.post(self.name + '_select')
            self.machine._set_machine_var(name=self.name + '_chars_entered',
                value=self.machine.machine_vars[self.name + '_chars_entered'] +
                      self.selected_char)

            if (len(self.machine.machine_vars[self.name + '_chars_entered']) ==
                    self.config['max_chars']):
                self.complete()

    def render(self):
        back_surface = (
            self.machine.images[self.config['back_char']].image_surface)
        end_surface = (
            self.machine.images[self.config['end_char']].image_surface)

        total_width = len(self.char_list) * self.config['char_width'] + (
            back_surface.get_width() + end_surface.get_width() +
            (self.config['image_padding'] * 4))

        self.create_element_surface(total_width, self.config['height'])

        current_x_position = 0

        for index, x in enumerate(self.char_list):

            if x == 'back':
                char_surface = back_surface
                next_offset = char_surface.get_width() + (
                    2 * self.config['image_padding'])
                x_offset = self.config['image_padding']

            elif x == 'end':
                char_surface = end_surface
                next_offset = char_surface.get_width() + (
                    2 * self.config['image_padding'])
                x_offset = self.config['image_padding']
            else:
                char_surface = self.fonts.render(text=x, **self.config)

                next_offset = self.config['char_width']
                x_offset = (((self.config['char_width'] -
                              char_surface.get_width()) / 2) +
                            self.config['char_x_offset'])

            if index == self.cursor_position:

                if x == 'back':
                    char_surface = self.machine.images[
                        self.config['back_char_selected']].image_surface
                    bg_width = char_surface.get_width() + (
                        2 * self.config['image_padding'])
                elif x == 'end':
                    char_surface = self.machine.images[
                        self.config['end_char_selected']].image_surface
                    bg_width = char_surface.get_width() + (
                        2 * self.config['image_padding'])
                else:
                    highlighted_config = deepcopy(self.config)
                    highlighted_config['color'] = (
                        self.config['selected_char_color'])
                    highlighted_config['bg_color'] = (
                        self.config['selected_char_bg'])
                    char_surface = self.fonts.render(text=x,
                                                     **highlighted_config)
                    bg_width = self.config['char_width']

                pygame.draw.rect(self.element_surface,
                                 self.config['selected_char_bg'],
                                 (current_x_position, # left
                                  0, # top
                                  bg_width, # width
                                  self.config['height'])) # height

            self.element_surface.blit(char_surface, (
                current_x_position+x_offset, self.config['char_y_offset']))

            current_x_position += next_offset

        # reduce the element surface to the width specified:
        if self.config['width']:
            rendered_char_surface = self.element_surface
            self.create_element_surface(self.config['width'],
                                        self.config['height'])

            h_offset = (rendered_char_surface.get_width() -
                        self.config['width']) / -2
            self.element_surface.blit(rendered_char_surface, (h_offset, 0))

        self.set_position(self.x, self.y, self.h_pos, self.v_pos)
        self.dirty = True
        self.slide.refresh(force_dirty=True)

    def complete(self):
        self.scrub()

        name = self.machine.machine_vars[self.name + '_chars_entered']

        if not name:
            name = ' '

        self.machine.machine_vars[self.name + '_chars_entered'] = ''

        return_param = {self.config['return_param']:
            self.config['text_variables'][self.config['return_param']]}

        self.machine.send(bcp_command='trigger',
                          name=self.name + '_complete',
                          player_name=name,
                          **return_param)

    def scrub(self):
        self.machine.events.remove_handlers_by_keys(
            self.registered_event_handlers)
        self.registered_event_handlers = list()


display_element_class = CharacterPicker
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
