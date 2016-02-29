from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class GiPlayer(ConfigPlayer):
    config_file_section = 'gi_player'
    show_section = 'gis'


    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        for gi, s in settings.items():
            gi.enable(s['brightness'])

    def validate_config(self, config):
        # config is localized to the 'gis' section of a show or the
        # 'gi_player' section of config

        if not config:
            config = dict()

        if not isinstance(config, dict):
            raise ValueError("Received invalid gi player config: {}"
                             .format(config))

        validated_config = dict()

        for gi, value in config.items():
            value = Util.hex_string_to_int(str(value))
            if 'tag|' in gi:
                tag = gi.split('tag|')[1]
                gi_list = self.machine.gis.sitems_tagged(tag)

                if not gi_list:
                    self.log.warning("No GI strings exist for tag '{}'".format(
                        tag))

            else:  # create a single item list of the gi
                try:
                    # run it through machine.gis to make sure it's valid
                    gi_list = [self.machine.gi[gi].name]
                except KeyError:
                    raise ValueError("Found invalid GI name '{}' in "
                                     "gi show or gi_player "
                                     "config".format(gi))

            for gi_ in gi_list:
                validated_config[gi_] = dict(brightness=value)

        return validated_config

    def process_config(self, config, **kwargs):
        # config is a validated config section:

        processed_config = dict()

        for gi_name, settings_dict in config.items():
            processed_config[self.machine.gi[gi_name]] = settings_dict

        return processed_config









player_cls = GiPlayer
