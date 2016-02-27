from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class TriggerPlayer(ConfigPlayer):
    config_file_section = 'trigger_player'
    show_section = 'triggers'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)
        for trigger, s in settings.items():
            self.machine.bcp.bcp_trigger(trigger, **s)

    def validate_config(self, config):
        if not config:
            config = dict()

        if type(config) is str:
            config = Util.string_to_list(config)

        if type(config) is list:
            final_dict = dict()
            for trigger in config:
                final_dict[trigger] = dict()
            return final_dict
        elif isinstance(config, dict):
            return config
        else:
            raise ValueError("Cannot process trigger config: {}".format(
                config))

    def process_config(self, config, **kwargs):
        # config is a validated config section:
        return config


player_cls = TriggerPlayer
