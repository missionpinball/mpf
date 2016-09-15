"""Flasher config player."""
from copy import deepcopy
from mpf.config_players.device_config_player import DeviceConfigPlayer


class FlasherPlayer(DeviceConfigPlayer):

    """Triggers flashers based on config."""

    config_file_section = 'flasher_player'
    show_section = 'flashers'

    def play(self, settings, context, priority=0, **kwargs):
        """Flash flashers."""
        del kwargs

        for flasher, s in settings.items():
            s = deepcopy(s)
            try:
                flasher.flash(**s)
            except AttributeError:
                self.machine.flashers[flasher].flash(**s)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(ms=None)

player_cls = FlasherPlayer
