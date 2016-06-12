"""Trigger config player."""
from mpf.core.config_player import ConfigPlayer


class TriggerPlayer(ConfigPlayer):

    """Executes BCP triggers based on config."""

    config_file_section = 'trigger_player'
    show_section = 'triggers'

    def play(self, settings, context, priority=0, **kwargs):
        """Execute BCP triggers."""
        del kwargs

        if 'triggers' in settings:
            settings = settings['triggers']

        for trigger, s in settings.items():
            self.machine.bcp.bcp_trigger(trigger, **s)

    def get_express_config(self, value):
        """Not supported."""
        del value
        raise NotImplementedError("Trigger Player does not support express config")


player_cls = TriggerPlayer
