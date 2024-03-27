from mpf.config_players.plugin_player import PluginPlayer


class MpfSoundPlayer(PluginPlayer):
    """Base class for part of the sound player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        sound_player=mpfmc.config_players.sound_player:register_with_mpf

    """
    config_file_section = 'sound_player'
    show_section = 'sounds'

    def get_express_config(self, value):
        """Parse express config."""
        return {"action": value}


player_cls = MpfSoundPlayer


def register_with_mpf(machine):
    """Registers the sound player plug-in with MPF"""
    return 'sound', MpfSoundPlayer(machine)
