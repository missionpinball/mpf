from mpf.core.config_player import ConfigPlayer


class TriggerPlayer(ConfigPlayer):
    config_file_section = 'trigger_player'
    show_section = 'triggers'

    def play(self, settings, key=None, priority=0, **kwargs):
        del kwargs

        if 'triggers' in settings:
            settings = settings['triggers']

        for trigger, s in settings.items():
            self.machine.bcp.bcp_trigger(trigger, **s)


player_cls = TriggerPlayer
