from mpf.core.config_player import ConfigPlayer


class GiPlayer(ConfigPlayer):
    config_file_section = 'gi_player'
    show_section = 'gis'

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=0,
             play_kwargs=None, **kwargs):

        del kwargs

        if 'gis' in settings:
            settings = settings['gis']

        for gi, s in settings.items():
            try:
                gi.enable(**s)
            except AttributeError:
                self.machine.gis[gi].enable(**s)

    def get_express_config(self, value):
        value = str(value)

        if value.lower() in ('off', 'disable'):
            value = '0'
        elif value.lower() in ('on', 'enable'):
            value = 'ff'

        return dict(brightness=value)

player_cls = GiPlayer
