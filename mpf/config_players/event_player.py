"""Event Config Player."""
from copy import deepcopy
from mpf.config_players.flat_config_player import FlatConfigPlayer
from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util


class EventPlayer(FlatConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'event_player'
    show_section = 'events'
    device_collection = None

    def __init__(self, machine):
        """Initialise EventPlayer."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine.delayRegistry)

    def play(self, settings, context, priority=0, **kwargs):
        """Post (delayed) events."""
        for event, s in settings.items():
            s = deepcopy(s)
            s.update(kwargs)
            if '|' in event:
                event, delay = event.split("|")
                delay = Util.string_to_ms(delay)
                self.delay.add(callback=self._post_event, ms=delay,
                               event=event, s=s)
            elif ':' in event:
                event, delay = event.split(":")
                delay = Util.string_to_ms(delay)
                self.delay.add(callback=self._post_event, ms=delay,
                               event=event, s=s)
            else:
                self.machine.events.post(event, **s)

    def _post_event(self, event, s):
        self.machine.events.post(event, **s)

    def get_list_config(self, value):
        """Parse list."""
        result = {}
        for event in value:
            result[event] = {}
        return result

    def get_express_config(self, value):
        """Parse short config."""
        return self.get_list_config(Util.string_to_list(value))


player_cls = EventPlayer
