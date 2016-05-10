from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class LightPlayer(ConfigPlayer):
    config_file_section = 'light_player'
    show_section = 'lights'
    machine_collection_name = 'lights'

    def play(self, settings, key=None, priority=0, **kwargs):
        del kwargs

        if 'lights' in settings:
            settings = settings['lights']

        for light, s in settings.items():
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            try:
                light.on(key=key, **s)
                try:
                    self.caller_target_map[key].add(light)
                except KeyError:
                    self.caller_target_map[key] = set()
                    self.caller_target_map[key].add(light)

            except AttributeError:
                try:
                    self._light_on(light, key=key, **s)
                except KeyError:
                    light_list = Util.string_to_list(light)
                    if len(light_list) > 1:
                        for light1 in light_list:
                            self._light_on(light1, key=key, **s)
                    else:
                        for light1 in self.machine.lights.sitems_tagged(light):
                            self._light_on(light1, key=key, **s)

    def _light_on(self, light_name, key=None, **s):
        light = self.machine.lights[light_name]
        light.on(key=key, **s)
        try:
            self.caller_target_map[key].add(light)
        except KeyError:
            self.caller_target_map[key] = set()
            self.caller_target_map[key].add(light)

    def clear(self, key):
        try:
            for light in self.caller_target_map[key]:
                light.remove_from_stack_by_key(key)
        except KeyError:
            pass

    def config_play_callback(self, settings, priority=0, mode=None,
                             hold=None, **kwargs):
        # led_player sections from config should set LEDs to hold

        super().config_play_callback(settings=settings, priority=priority,
                                     mode=mode, hold=True, **kwargs)

        # todo change this in the base method?

    def get_express_config(self, value):
        value = str(value).replace(' ', '').lower()
        fade = 0
        if '-f' in value:
            composite_value = value.split('-f')
            value = composite_value[0]
            fade = Util.string_to_ms(composite_value[1])

        return dict(brightness=value, fade=fade)

    def get_full_config(self, value):
        super().get_full_config(value)
        value['fade_ms'] = value.pop('fade')
        return value

player_cls = LightPlayer
