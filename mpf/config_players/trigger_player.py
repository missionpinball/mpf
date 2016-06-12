from mpf.core.config_player import ConfigPlayer


class TriggerPlayer(ConfigPlayer):
    config_file_section = 'trigger_player'
    show_section = 'triggers'

    def play(self, settings, context, priority=0, **kwargs):
        del kwargs

        if 'triggers' in settings:
            settings = settings['triggers']

        for trigger, s in settings.items():
            self.machine.bcp.bcp_trigger(trigger, **s)

    def get_express_config(self, value):
        del value
        raise NotImplementedError("Trigger Player does not support express config")


player_cls = TriggerPlayer
