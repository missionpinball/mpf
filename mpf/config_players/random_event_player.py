"""Random event config player."""
import random

from mpf.config_players.flat_config_player import FlatConfigPlayer
from mpf.core.utility_functions import Util


class RandomEventPlayer(FlatConfigPlayer):

    """Plays a random event based on config."""

    config_file_section = 'random_event_player'
    show_section = 'random_events'
    device_collection = None

    def play(self, settings, context, priority=0, **kwargs):
        """Play a random event from list based on config."""
        del context
        del priority
        self.machine.events.post(random.choice(settings['event_list']), **kwargs)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(event_list=Util.string_to_list(value))

    def get_list_config(self, value):
        """Parse list."""
        return dict(event_list=value)

    def get_full_config(self, value):
        """No further validation in here."""
        return value


player_cls = RandomEventPlayer
