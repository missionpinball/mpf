from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class FlasherPlayer(ConfigPlayer):
    config_file_section = 'flasher_player'
    show_section = 'flashers'

    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        if 'flashers' in settings:
            settings = settings['flashers']

        for flasher, s in settings.items():
            try:
                flasher.flash(**s)
            except AttributeError:
                self.machine.flashers[flasher].flash(**s)

    def get_express_config(self, value):
        return dict(ms=None)

player_cls = FlasherPlayer
