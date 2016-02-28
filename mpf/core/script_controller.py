from copy import deepcopy
import re

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util
from mpf.assets.show import Show
from mpf.core.config_player import ConfigPlayer


class Script(object):

    def __init__(self, script_data):
        self.script_data = script_data
        self.tokens = set()
        self.token_values = dict()
        self.token_keys = dict()
        """dict of tokens:

        token_name:
            - path:
            - type: 'key' or 'value'

        """
        self.token_finder = re.compile('(?<=%)(.*?)(?=%)')

        self._parse_script()

    def _add_token(self, token, path, token_type):

        if token not in self.tokens:
            self.tokens.add(token)

        if token_type == 'key':
            if token not in self.token_keys:
                self.token_keys[token] = list()
            self.token_keys[token].append(path)

        elif token_type == 'value':
            if token not in self.token_values:
                self.token_values[token] = list()
            self.token_values[token].append(path)

    def _parse_script(self):
        if isinstance(self.script_data, dict):
            self.script_data = list(self.script_data)

        self._walk_script(self.script_data)

    def _check_token(self, path, data, token_type):
        try:
            token = self.token_finder.findall(data)
        except TypeError:
            return

        if token:
            self._add_token(token[0], path, token_type)

    def _walk_script(self, data, path=None, list_index=None):

        # walks a list of dicts, checking tokens

        if not path:
            path = list()

        if type(data) is dict:
            for k, v in data.items():
                self._check_token(path, k, 'key')
                self._walk_script(v, path + [k])

        elif type(data) is list:
            for i in data:
                self._check_token(path, i, 'key')
                if list_index is None:
                    list_index = 0
                else:
                    list_index += 1
                self._walk_script(i, path + [list_index], list_index)

        else:
            self._check_token(path, data, 'value')

    def generate_show(self, **kwargs):
        pass

    def _replace_tokens(self, **kwargs):
        keys_replaced = dict()
        script = deepcopy(self.script_data)

        for token, replacement in kwargs.items():
            if token in self.token_values:
                for token_path in self.token_values[token]:
                    target = script
                    for x in token_path[:-1]:
                        target = target[x]

                    target[token_path[-1]] = replacement

        for token, replacement in kwargs.items():
            if token in self.token_keys:
                key_name = '%{}%'.format(token)
                for token_path in self.token_keys[token]:
                    target = script
                    for x in token_path:
                        if x in keys_replaced:
                            x = keys_replaced[x]

                        target = target[x]

                    target[replacement] = target.pop(key_name)
                    keys_replaced[key_name] = replacement

        return script






























class ScriptController(object):

    id = 0

    @classmethod
    def get_id(cls):
        cls.id += 1
        return cls.id

    def __init__(self, machine):
        self.machine = machine
        self.registered_scripts = CaseInsensitiveDict()

        try:
            self._process_config_scripts_section(self.machine.config['scripts'])
        except KeyError:
            pass

        self.machine.mode_controller.register_load_method(
            self._process_config_scripts_section, 'scripts')

    def register_script(self, name, settings):
        if name in self.registered_scripts:
            raise ValueError("Script named '{}' was just registered, but "
                             "there's already a registered script with that "
                             "name. Scripts are shared machine-wide")
        else:
            self.registered_scripts[name] = settings

    def _process_config_scripts_section(self, config, **kwargs):
        # processes the scripts section of a mode or machine config
        del kwargs

        for script, settings in config.items():
            if isinstance(settings, dict):
                settings = [settings]

            for i, setting in enumerate(settings):
                settings[i] = self.machine.config_validator.validate_config(
                    'scripts', setting)

            # todo more here?

            self.register_script(script, settings)

    def create_show_from_script(self, script, devices, name, key=None,
                                **kwargs):
        """Creates a show from a script.

        Args:
            script: Python dictionary in script format
            key: Object (typically string) that will be used to stop the show
                created by this list later.

        """

        show_data = list()
        final_device_dict = dict()

        # devices is dict
        for device_name, device_list in devices.items():
            device_list = Util.string_to_list(device_list)

            expanded_device_list = list()
            for device in device_list:

                if 'tag|' in device:

                    device_collection = (
                        ConfigPlayer.show_players[device_name].device_collection)

                    expanded_device_list.extend(
                        device_collection.sitems_tagged(device.strip('tag|')))

                else:
                    expanded_device_list.append(device)

            if expanded_device_list:
                final_device_dict[device_name] = expanded_device_list

        for step in script:
            this_step_settings = deepcopy(step)
            for device_class, device_list in final_device_dict.items():
                for setting in step.keys():
                    if setting in ConfigPlayer.show_players[device_class].valid_keys:
                        this_step_settings[setting] = step[setting]

                this_step_settings[device_class] = device_list

            show_data.append(this_step_settings)

        print(show_data)

        return Show(machine=self.machine, name=name, file=None,
                    steps=show_data)

    def run_registered_script(self, script, devices, **kwargs):

        try:
            return self.run_script(
                script=self.registered_scripts[script], devices=devices,
                name='script_{}_{}'.format(script, ScriptController.get_id()),
                **kwargs)
        except KeyError:
            raise ValueError("Warning. Script '%s' not found", script)

    def run_script(self, script, devices, name=None, loops=-1, callback=None,
                   key=None, **kwargs):
        """Runs a script.

        Args:
            script: A list of dictionaries of script commands. (See below).
            devices: dict of device names to mappings
            loops: The number of times the script loops/repeats (-1 =
                indefinitely).
            callback: A method that will be called when this script stops.
            key: A key that can be used to later stop the light show this
                script
                creates. Typically a unique string. If it's not passed, it will
                either be the first light name or the first LED name.
            **kwargs: Since this method just builds a Light Show, you can use
                any other Light Show attribute here as well, such as
                playback_rate, blend, repeat, loops, etc.

        Returns:
            :class:`Show` object. Since running a script just sets up and
            runs a regular Show, run_script returns the Show object.
            In most cases you won't need this, but it's nice if you want to
            know exactly which Show was created by this script so you can
            stop it later. (See the examples below for usage.)

        Example:
        - time: 0
          color: ff
        - time: +1
          color: 0
        - time: +1


        """

        if not name:
            name = 'script_unnamed_{}'.format(ScriptController.get_id())

        show = self.create_show_from_script(script, devices, name)


        self.machine.show_controller.play_show(show=show, loops=loops,
                                               callback=callback, **kwargs)

        return show

    def stop_script(self, key, **kwargs):
        """Stops and removes the show that was created by a script.

        Args:
            key: The key that was specified in run_script().
            **kwargs: Not used, included in case this method is called via an
                event handler that might contain other random paramters.

        """
        del kwargs

        try:
            self.stop_show(show=self.running_show_keys[key], **kwargs)
            del self.running_show_keys[key]
        except KeyError:
            pass
