from mpf.core.config_player import ConfigPlayer


class TriggerPlayer(ConfigPlayer):
    config_file_section = 'trigger_player'
    show_section = 'triggers'

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=None,
             play_kwargs=None, **kwargs):

        del kwargs

        super().play(settings, mode, caller, priority, play_kwargs)

        if 'triggers' in settings:
            settings = settings['triggers']

        for trigger, s in settings.items():
            self.machine.bcp.bcp_trigger(trigger, **s)


player_cls = TriggerPlayer
