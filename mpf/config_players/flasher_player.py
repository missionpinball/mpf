from mpf.core.config_player import ConfigPlayer


class FlasherPlayer(ConfigPlayer):
    config_file_section = 'flasher_player'
    show_section = 'flashers'

    def _play(self, settings, key, priority, play_kwargs, **kwargs):
        del kwargs

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
