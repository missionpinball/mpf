from mpf.core.config_player import ConfigPlayer


class PluginPlayer(ConfigPlayer):

    def play(self, settings, mode=None, caller=None, **kwargs):
        """Called when a plugged-in config_player needs to play something.

        Sends the play command, and associated config, to the remote player
        via BCP.
        """
        print(self.show_section, settings, mode, caller, kwargs)
