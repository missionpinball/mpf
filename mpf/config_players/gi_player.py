"""GI config player."""
from mpf.core.config_player import ConfigPlayer


class GiPlayer(ConfigPlayer):

    """Enables GIs based on config."""

    config_file_section = 'gi_player'
    show_section = 'gis'

    def play(self, settings, context, priority=0, **kwargs):
        """Enable GIs."""
        del kwargs

        if 'gis' in settings:
            settings = settings['gis']

        for gi, s in settings.items():
            try:
                gi.enable(**s)
            except AttributeError:
                self.machine.gis[gi].enable(**s)

    def get_express_config(self, value):
        """Parse express config."""
        value = str(value)

        if value.lower() in ('off', 'disable'):
            value = '0'
        elif value.lower() in ('on', 'enable'):
            value = 'ff'

        return dict(brightness=value)

player_cls = GiPlayer
