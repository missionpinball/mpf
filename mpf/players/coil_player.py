from mpf.core.config_player import ConfigPlayer


class CoilPlayer(ConfigPlayer):
    config_file_section = 'coil_player'
    show_section = 'coils'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)
        for coil, s in settings.items():
            getattr(coil, s['action'])(**s)

    def validate_config(self, config):

        if not config:
            config = dict()

        if not isinstance(config, dict):
            raise ValueError("Received invalid coil player config: "
                             .format(config))

        for coil, settings in config.items():
            if not settings:
                settings = dict()
            settings = self.machine.config_validator.validate_config('coil_player',
                                                                   settings)
            if settings['action'] not in ('pulse', 'enable', 'disable',
                                        'timed_enable'):
                raise ValueError("Invalid coin action type: {}".format(settings[
                                                                       'action']))

            if not settings['ms']:
                del settings['ms']
            else:
                settings['milliseconds'] = settings.pop('ms')


            final_settings = dict()
            for k, v in settings.items():
                if v is not None:
                    final_settings[k] = v

            config[coil] = final_settings

        return config

    def process_config(self, config, **kwargs):
        processed_config = dict()

        for coil_name, settings_dict in config.items():
            processed_config[self.machine.coils[coil_name]] = settings_dict

        return processed_config

player_cls = CoilPlayer
