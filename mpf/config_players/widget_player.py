from mpf.config_players.plugin_player import PluginPlayer


class MpfWidgetPlayer(PluginPlayer):

    """Widget Player in MPF.

    Note: This class is loaded by MPF and everything in it is in the context of MPF.
    """

    config_file_section = 'widget_player'
    show_section = 'widgets'


def register_with_mpf(machine):
    """Register widget player in MPF module."""
    return 'widget', MpfWidgetPlayer(machine)


player_cls = MpfWidgetPlayer
