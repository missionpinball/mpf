"""Event Config Player."""
from copy import deepcopy

from mpf.core.placeholder_manager import TextTemplate

from mpf.config_players.flat_config_player import FlatConfigPlayer
from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util


class EventPlayer(FlatConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'event_player'
    show_section = 'events'

    def __init__(self, machine):
        """Initialise EventPlayer."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine.delayRegistry)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Post (delayed) events."""
        del kwargs
        for event, s in settings.items():
            s = deepcopy(s)
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
                self._post_event(event, s)

    def _post_event(self, event, s):
        event_name_placeholder = TextTemplate(self.machine, event.replace(".", "|"))
        self.machine.events.post(event_name_placeholder.evaluate(), **s)

    def get_list_config(self, value):
        """Parse list."""
        result = {}
        for event in value:
            result[event] = {}
        return result

    def get_express_config(self, value):
        """Parse short config."""
        return self.get_list_config(Util.string_to_list(value))
