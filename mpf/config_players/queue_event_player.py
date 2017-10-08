"""Queue Event Config Player."""
from functools import partial

from mpf.core.config_player import ConfigPlayer


class QueueEventPlayer(ConfigPlayer):

    """Posts queue events based on config."""

    config_file_section = 'queue_event_player'

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Post queue events."""
        del kwargs
        del calling_context
        if settings['events_when_finished']:
            self.machine.events.post_queue(
                settings['queue_event'],
                callback=partial(self._callback,
                                 settings['events_when_finished'],
                                 settings['args']),
                **settings['args'])
        else:
            self.machine.events.post_queue(settings['queue_event'],
                                           **settings['args'])

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = self._parse_config(settings, name)
        return config

    def _callback(self, event, s):
        self.machine.events.post(event, **s)

    def get_express_config(self, value):
        """No express config."""
        raise AssertionError("Not supported")
