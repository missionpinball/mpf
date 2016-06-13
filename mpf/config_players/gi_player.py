"""GI config player."""
from mpf.core.config_player import ConfigPlayer


class GiPlayer(ConfigPlayer):

    """Enables GIs based on config."""

    config_file_section = 'gi_player'
    show_section = 'gis'

    def play(self, settings, context, priority=0, **kwargs):
        """Enable GIs."""
        del kwargs
        instance_dict = self._get_instance_dict(context)

        if 'gis' in settings:
            settings = settings['gis']

        for gi, s in settings.items():
            try:
                gi.enable(**s)
                instance_dict[gi.name] = gi
            except AttributeError:
                self.machine.gis[gi].enable(**s)
                instance_dict[gi] = self.machine.gis[gi]

    def get_express_config(self, value):
        """Parse express config."""
        value = str(value)

        if value.lower() in ('off', 'disable'):
            value = '0'
        elif value.lower() in ('on', 'enable'):
            value = 'ff'

        return dict(brightness=value)

    def clear_context(self, context):
        """Disable all used GIs at the end."""
        instance_dict = self._get_instance_dict(context)
        for gi in instance_dict.values():
            gi.disable()

        self._reset_instance_dict(context)

player_cls = GiPlayer
