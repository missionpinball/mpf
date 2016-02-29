from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class LightPlayer(ConfigPlayer):
    config_file_section = 'light_player'
    show_section = 'lights'
    machine_collection_name = 'lights'

    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        for light, s in settings.items():
            self.caller_target_map[caller].add(light)
            light.on(**s)

    def clear(self, caller, priority):
        try:
            for light in self.caller_target_map[caller]:
                light.off(priority=priority)
        except KeyError:
            pass

    def validate_config(self, config):
        # config is localized to the 'lights' section of a show or the
        # 'light_player' section of config

        if not config:
            config = dict()

        if not isinstance(config, dict):
            raise ValueError("Received invalid light player config: {}"
                             .format(config))

        validated_config = dict()

        for light, value in config.items():
            value = str(value)
            if 'tag|' in light:
                tag = light.split('tag|')[1]
                light_list = self.machine.lights.sitems_tagged(tag)

                if not light_list:
                    self.log.warning("No lights exist for tag '{"
                                     "}'".format(tag))

            else:  # create a single item list of the light
                try:
                    # run it through machine.lights to make sure it's valid
                    light_list = [self.machine.lights[light].name]
                except KeyError:
                    raise ValueError("Found invalid light name '{}' in "
                                     "light show or light_player "
                                     "config".format(light))

            # convert / ensure lights are single ints
            fade = 0

            if '-f' in value:
                composite_value = value.split('-f')
                value = composite_value[0]
                fade = Util.string_to_ms(composite_value[1])

            brightness = max(min(Util.hex_string_to_int(value), 255), 0)

            for light_ in light_list:
                validated_config[light_] = dict(brightness=brightness,
                                                fade_ms=fade)

        return validated_config

    def process_config(self, config, **kwargs):
        # config is a validated config section:
        processed_config = dict()

        for light_name, settings_dict in config.items():
            processed_config[self.machine.lights[light_name]] = settings_dict

        return processed_config

    def process_show_config(self, config, **kwargs):
        # config is a validated config section:
        processed_config = dict()

        for light_name, settings_dict in config.items():
            processed_config[self.machine.lights[light_name]] = settings_dict

        return processed_config

player_cls = LightPlayer
