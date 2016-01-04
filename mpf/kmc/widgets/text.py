import re

from kivy.uix.label import Label


class Text(Label):

    var_finder = re.compile("(?<=%)[a-zA-Z_0-9|]+(?=%)")

    def __init__(self, mc, text_variables=None, **kwargs):

        # what do we want here?
        # color
        # opacity
        # font?
        # size
        # x, y
        # h_pos --> valign
        # v_pos --> halign
        # layer. priority?
        # mode
        # screen (or display?)

        # self.pos = (0, 0)
        # self.size = (1024, 768)
        # self.pos_hint = {'top': 1}

        self.mc = mc
        self.original_text = kwargs.get('text', '')
        # self.fonts = mc.fonts

        self.config = kwargs

        self.text_variables = dict()

        self._process_text(self.text, local_replacements=text_variables,
                           local_type='event')

        self.size_hint = (None, None)

        kwargs['size_hint']=(None, None)

        super(Text, self).__init__()

        self.texture_update()
        self.size = self.texture_size
        # self.pos = (100, 100)



    def _get_text_vars(self):
        return Text.var_finder.findall(self.original_text)

    def _process_text(self, text, local_replacements=None, local_type=None):
        # text: source text with placeholder vars
        # local_replacements: dict of var names & their replacements
        # local_type: type specifier of local replacements. e.g. "event" means
        # it will look for %event|var_name% in the text string

        text = str(text)

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

        if self._get_text_vars():
            self._setup_variable_monitors()

        self.update_vars_in_text()

    def update_vars_in_text(self):

        text = self.original_text

        for var_string in self._get_text_vars():
            if var_string.startswith('machine|'):
                try:
                    text = text.replace('%' + var_string + '%',
                        str(self.machine.machine_vars[var_string.split('|')[1]]))
                except KeyError:
                    text = ''

            elif self.machine.player:
                if var_string.startswith('player|'):
                    text = text.replace('%' + var_string + '%',
                                        str(self.machine.player[var_string.split('|')[1]]))
                elif var_string.startswith('player'):
                    player_num, var_name = var_string.lstrip('player').split('|')
                    try:
                        value = self.machine.player_list[int(player_num)-1][var_name]

                        if value is not None:
                            text = text.replace('%' + var_string + '%', str(value))
                        else:
                            text = ''
                    except IndexError:
                        text = ''
                else:
                    text = text.replace('%' + var_string + '%',
                                        str(self.machine.player[var_string]))

        self.update_text(text)

    def update_text(self, text):
        # todo auto-fit text to a certain size bounding box

        text = str(text)

        if text:
            if 'min_digits' in self.config:
                text = text.zfill(self.config['min_digits'])

            if ('number_grouping' in self.config and
                    self.config['number_grouping']):

                # find the numbers in the string
                number_list = [s for s in text.split() if s.isdigit()]

                # group the numbers and replace them in the string
                for item in number_list:
                    grouped_item = self.group_digits(item)
                    text = text.replace(str(item), grouped_item)

            # Are we set up for multi-language?
            # if self.language:
            #     text = self.language.text(text)

        self.text = text
        # self.render()

    def _player_var_change(self, **kwargs):
        self.update_vars_in_text()

    def _machine_var_change(self, **kwargs):
        self.update_vars_in_text()

    def _setup_variable_monitors(self):
        for var_string in self._get_text_vars():
            if '|' not in var_string:
                self.add_player_var_handler(name=var_string, player=None)
            else:
                source, variable_name = var_string.split('|')
                if source.lower().startswith('player'):

                    if source.lstrip('player'):
                        self.add_player_var_handler(name=variable_name,
                            player=source.lstrip('player'))
                    else:
                        self.add_player_var_handler(name=var_string,
                            player=self.machine.player['number'])

                elif source.lower() == 'machine':
                    self.add_machine_var_handler(name=variable_name)

    def add_player_var_handler(self, name, player):
        self.machine.events.add_handler('player_' + name,
                                        self._player_var_change,
                                        target_player=player,
                                        var_name=name)

    def add_machine_var_handler(self, name):
        self.machine.events.add_handler('machine_var_' + name,
                                        self._machine_var_change,
                                        var_name=name)

    def scrub(self):
        self.machine.events.remove_handler(self._player_var_change)
        self.machine.events.remove_handler(self._machine_var_change)

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