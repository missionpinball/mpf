"""Trigger config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class TriggerPlayer(DeviceConfigPlayer):

    """Executes BCP triggers based on config."""

    config_file_section = 'trigger_player'
    show_section = 'triggers'

    def play(self, settings, context, priority=0, **kwargs):
        """Execute BCP triggers."""
        del kwargs

        for trigger, s in settings.items():
            self.machine.bcp.bcp_trigger(trigger, **s)

    def get_express_config(self, value):
        """Not supported."""
        del value
        raise NotImplementedError("Trigger Player does not support express config")


player_cls = TriggerPlayer
