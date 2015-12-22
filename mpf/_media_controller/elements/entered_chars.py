"""Contains the parent class of the EnteredChars DisplayElement"""

# character_picker.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.media_controller.core.display import DisplayElement
import mpf.media_controller.decorators


class EnteredChars(DisplayElement):

    def __init__(self, slide, machine, x=None, y=None, h_pos=None,
                     v_pos=None, layer=0, **kwargs):

        super(EnteredChars, self).__init__(slide, x, y, h_pos, v_pos, layer)

        self.fonts = machine.display.fonts
        self.slide = slide
        self.machine = machine
        self.layer = layer
        self.config = kwargs
        self.cursor_element = None

        if 'character_picker' not in self.config:
            self.config['character_picker'] = 'character_picker'

        if 'cursor_char' not in self.config:
            self.config['cursor_char'] = '_'

        if 'cursor_offset_x' not in self.config:
            self.config['cursor_offset_x'] = 0

        if 'cursor_offset_y' not in self.config:
            self.config['cursor_offset_y'] = 0

        self.adjust_colors(**self.config)

        self.config['color'] = self.adjusted_color
        self.config['bg_color'] = self.adjusted_bg_color

        self.machine.events.add_handler('machine_var_' + self.config['character_picker'] + '_chars_entered',
                                        self.render)

        self.render()

    def scrub(self):
        self.machine.events.remove_handler(self.render)

    def render(self, value='', **kwargs):

        char_surface = self.fonts.render(text=value, **self.config)

        self.create_element_surface(char_surface.get_width(), char_surface.get_height())
        self.element_surface.blit(char_surface, (0,0))
        self.set_position(self.x, self.y, self.h_pos, self.v_pos)
        self.dirty = True

        self.update_cursor()

        self.slide.refresh(force_dirty=True)

    def update_cursor(self):
        if not self.cursor_element:
            self.cursor_element = self.create_cursor_element()
        else:
            self.cursor_element.set_position(
                x=self.x + self.element_surface.get_width() +
                  self.config['cursor_offset_x'],
                y=self.y + self.config['cursor_offset_y'],
                h_pos=self.h_pos,
                v_pos=self.v_pos)

    def create_cursor_element(self):
        element = self.slide.add_element(
            element_type='text',
            name='cursor',
            text='_',
            x=self.x + self.element_surface.get_width() +
              self.config['cursor_offset_x'],
            y=self.y + self.config['cursor_offset_y'],
            h_pos=self.h_pos,
            v_pos=self.v_pos)

        if 'cursor_decorators' in self.config:

            if type(self.config['cursor_decorators']) is dict:  # We have settings

                decorator_class = eval('mpf.media_controller.decorators.' +
                    self.config['cursor_decorators']['type'] + '.' +
                    self.machine.display.decorators[
                    self.config['cursor_decorators']['type']][1])

                element.attach_decorator(decorator_class(element,
                                                    **self.config['cursor_decorators']))

            elif type(self.config['cursor_decorators']) is list:

                for decorator in self.config['cursor_decorators']:
                    decorator_class = eval('mpf.media_controller.decorators.' +
                        decorator['type'] + '.' +
                        self.machine.display.decorators[decorator['type']][1])

                element.attach_decorator(decorator_class(element, **decorator))

        return element


display_element_class = EnteredChars
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