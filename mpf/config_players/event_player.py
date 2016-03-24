from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util

class EventPlayer(ConfigPlayer):
    config_file_section = 'event_player'
    show_section = 'events'
    device_collection = None

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None,
             priority=0, play_kwargs=None, **kwargs):

        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        if 'events' in settings:
            settings = settings['events']

        for event, s in settings.items():
            s.update(play_kwargs)
            self.machine.events.post(event, **s)

    def get_express_config(self, value):
        return_dict = dict()
        return_dict[value] = dict()
        return return_dict

    def validate_config(self, config):
        # override because we want to let events just be a list of
        # events

        new_config = dict()

        for event, settings in config.items():
            if not isinstance(settings, list) or not isinstance(settings, dict):
                new_config[event] = dict()

                for event1 in Util.string_to_list(settings):
                    new_config[event][event1] = dict()

            else:
                new_config[event] = settings

        super().validate_config(new_config)

        return new_config

player_cls = EventPlayer
