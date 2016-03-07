from mpf.core.config_player import ConfigPlayer


class GiPlayer(ConfigPlayer):
    config_file_section = 'gi_player'
    show_section = 'gis'


    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        if 'gis' in settings:
            settings = settings['gis']

        for gi, s in settings.items():
            try:
                gi.enable(**s)
            except AttributeError:
                self.machine.gi[gi].enable(**s)

    def get_express_config(self, value):
        value = str(value)

        if value.lower() in ('off', 'disable'):
            value = '0'
        elif value.lower() in ('on', 'enable'):
            value = 'ff'

        return dict(brightness=value)

player_cls = GiPlayer
