from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class FlasherPlayer(ConfigPlayer):
    config_file_section = 'flasher_player'
    show_section = 'flashers'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)

        for flasher in settings:
            flasher.flash()

    def validate_config(self, config):
        if not config:
            config = list()

        config = Util.string_to_list(config)

        for flasher in config:
            if flasher not in self.machine.flashers:
                raise ValueError("Flasher '{}' is not a valid flasher "
                                 "name".format(flasher))

        return config

    def process_config(self, config, **kwargs):
        # config is a validated config section:
        new_list = list()

        for flasher in config:
            new_list.append(self.machine.flashers[flasher])

        return new_list

player_cls = FlasherPlayer
