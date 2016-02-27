from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util

class EventPlayer(ConfigPlayer):
    config_file_section = 'event_player'
    show_section = 'events'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)
        for event in settings:
            self.machine.events.post(event, **kwargs)

    def validate_config(self, config):
        if type(config) is dict:
            final_dict = dict()

            for trigger_event, play_events in config.items():
                final_dict[trigger_event] = Util.string_to_list(play_events)

            return final_dict

    def process_config(self, config, **kwargs):
        for event, settings in config.items():
            config[event] = Util.string_to_list(settings)

    def validate_show_config(self, config):
        return Util.string_to_list(config)

    def process_show_config(self, config, **kwargs):
        return config

player_cls = EventPlayer
