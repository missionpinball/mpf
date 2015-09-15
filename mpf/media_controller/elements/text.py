"""Contains the parent class of the Text DisplayElement"""

# text.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import re
from mpf.media_controller.core.display import DisplayElement


class Text(DisplayElement):
    """Represents an animation display element.

    Args:
        slide: The Slide object this animation is being added to.
        machine: The main machine object.
        text: A string of the text you'd like to display. If you have the
            multi-language plug-in enabled, this text will be run through the
            language engine before it's displayed.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at: https://missionpinball.com/docs/displays/display-elements/positioning/

    """

    def __init__(self, slide, machine, text, x=None, y=None, h_pos=None,
                 v_pos=None, layer=0, text_variables=None, **kwargs):

        super(Text, self).__init__(slide, x, y, h_pos, v_pos, layer)

        self.text = str(text)
        self.original_text = self.text
        self.fonts = machine.display.fonts
        self.language = machine.language
        self.slide = slide
        self.machine = machine

        self.config = kwargs

        self.var_finder = re.compile("(?<=%)[a-zA-Z0-9|]+(?=%)")

        if not text_variables:
            text_variables = dict()

        self.adjust_colors(**self.config)

        self.config['color'] = self.adjusted_color
        self.config['bg_color'] = self.adjusted_bg_color

        # Set defaults
        if 'name' in self.config:
            self.name = self.config['name']
        else:
            self.name = text

        self.text = self._process_text(self.text,
                                       local_replacements=text_variables,
                                       local_type='event')

        if self._get_text_vars():
            self._setup_variable_monitors()

        self.layer = layer

        self.element_surface = self.fonts.render(text=self.text, **self.config)
        self.set_position(self.x, self.y, self.h_pos, self.v_pos)

    def _get_text_vars(self):
        return self.var_finder.findall(self.original_text)

    def _process_text(self, text, local_replacements=None, local_type=None):
        # text: source text with placeholder vars
        # local_replacements: dict of var names & their replacements
        # local_type: type specifier of local replacements. e.g. "event" means
        # it will look for %event|var_name% in the text string

        if not local_replacements:
            local_replacements = list()

        for var_string in self._get_text_vars():
            if var_string in local_replacements:
                text = text.replace('%' + var_string + '%',
                                    str(local_replacements[var_string]))
                self.original_text = text

            elif local_type and var_string.startswith(local_type + '|'):
                text = text.replace('%' + var_string + '%',
                    str(local_replacements[var_string.split('|')[1]]))
                self.original_text = text

            elif self.machine.player:
                text = text.replace('%' + var_string + '%',
                                    str(self.machine.player[var_string]))

        if 'min_digits' in self.config:
            text = text.zfill(self.config['min_digits'])

        if 'number_grouping' in self.config and self.config['number_grouping']:

        # todo this only works for ints
        # todo move enabling this and separator char to config

            # find the numbers in the string
            number_list = [s for s in text.split() if s.isdigit()]

            # group the numbers and replace them in the string
            for item in number_list:
                grouped_item = self.group_digits(item)
                text = text.replace(str(item), grouped_item)

        # Are we set up for multi-language>
        if self.language:
            text = self.language.text(text)

        return text

    def _player_var_change(self, player_num, target_player, **kwargs):
        self.text = self._process_text(self.original_text)

        self.render()

    def _setup_variable_monitors(self):

        for var_string in self._get_text_vars():
            if '|' not in var_string:
                self.add_player_var_handler(name=var_string,
                                            player=self.machine.player['number'])
            else:
                source, name = var_string.split('|')

                if source.lower().startswith('player'):

                    if source.strip('player'):
                        self.add_player_var_handler(name=name,
                            player=source.strip('player'))
                    else:
                        self.add_player_var_handler(name=var_string,
                            player=self.machine.player['number'])

                elif source.lower() == 'machine':
                    # add machine monitor
                    pass

    def add_player_var_handler(self, name, player):
        self.machine.events.add_handler('player_' + name,
                                        self._player_var_change,
                                        target_player=player)

    def render(self):

        self.element_surface = self.fonts.render(text=self.text, **self.config)
        self.set_position(self.x, self.y, self.h_pos, self.v_pos)
        self.dirty = True

        self.slide.refresh()

        # todo add logic around color/shade
        # todo trim this to a certain size? Or force it to fit in the size?

    def scrub(self):
        self.machine.events.remove_handler(self._player_var_change)

    def group_digits(self, text, separator=',', group_size=3):
        """Enables digit grouping (i.e. adds comma separators between
        thousands digits).

        Args:
            text: The incoming string of text
            separator: String of the character(s) you'd like to add between the
                digit groups. Default is a comma. (",")
            group_size: How many digits you want in each group. Default is 3.

        Returns: A string with the separator added.

        MPF uses this method instead of the Python locale settings because the
        locale settings are a mess. They're set system-wide and it's really hard
        to make them work cross-platform and there are all sorts of external
        dependencies, so this is just way easier.

        """

        digit_list = list(text.split('.')[0])

        for i in range(len(digit_list))[::-group_size][1:]:
            digit_list.insert(i+1, separator)

        return ''.join(digit_list)


display_element_class = Text
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
