import random
import copy
from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class RandomEventPlayer(ConfigPlayer):
    config_file_section = 'random_event_player'
    show_section = 'random_events'
    device_collection = None

    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        these_settings = copy.deepcopy(settings)
        these_settings.update(kwargs)
        event_list = these_settings.pop('event_list')
        self.machine.events.post(random.choice(event_list), **kwargs)

    def get_express_config(self, value):
        return dict(event_list=Util.string_to_list(value))

    def validate_config(self, config):
        # override because we want to let events just be a list of
        # events

        new_config = dict()

        for event, settings in config.items():
            if not isinstance(settings, list) or not isinstance(settings, dict):
                new_config[event] = dict()
                new_config[event]['event_list'] = Util.string_to_list(settings)

            else:
                new_config[event] = settings

        super().validate_config(new_config)

        return new_config


player_cls = RandomEventPlayer
