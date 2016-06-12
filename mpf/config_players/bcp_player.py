"""Stub for BCP Player."""
from mpf.core.config_player import ConfigPlayer


class BcpPlayer(ConfigPlayer):

    """Dummy BCP Player."""

    config_file_section = 'bcp_player'
    show_section = 'bcp'

    def play(self, settings, context, priority=0, **kwargs):
        """Play BCP events."""
        pass

    def get_express_config(self, value):
        """Parse express config."""
        pass

player_cls = BcpPlayer
