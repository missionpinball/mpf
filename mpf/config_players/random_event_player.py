import random

from mpf.core.utility_functions import Util
from mpf.config_players.event_player import EventPlayer


class RandomEventPlayer(EventPlayer):
    config_file_section = 'random_event_player'
    show_section = 'random_events'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)
        self.machine.events.post(random.choice(settings['event_list']),
                                 **kwargs)

    def validate_config(self, config):
        if type(config) is dict:
            final_dict = dict()

            for trigger_event, play_events in config.items():
                final_dict[trigger_event] = Util.string_to_list(play_events)

            return final_dict

    def process_config(self, config, **kwargs):
        for event, settings in config.items():
            config[event] = dict(event_list=Util.string_to_list(settings))

player_cls = RandomEventPlayer
