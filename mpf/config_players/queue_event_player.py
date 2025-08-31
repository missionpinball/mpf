"""Queue Event Config Player."""
from typing import List

from functools import partial

from mpf.core.config_player import ConfigPlayer


class QueueEventPlayer(ConfigPlayer):

    """Posts queue events based on config."""

    config_file_section = 'queue_event_player'

    __slots__ = []  # type: List[str]

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Post queue events."""
        del kwargs
        del calling_context
        queue_event = settings['queue_event']
        events_when_finished = settings['events_when_finished'] or 'queue_event_complete'
        self.machine.events.post_queue(queue_event,
                                       callback=partial(self._callback,
                                                        events_when_finished,
                                                        queue_event=queue_event,
                                                        **settings['args']),
                                       **settings['args'])
        '''event: queue_event_complete
        desc: A queue event has completed and queue_event_player
        is reporting completion with a default handler
        args:
        queue_event: The name of the queue event (not the queue event player entry)
        **args: Any additional arguments defined in your queue_event_player under "args"
        '''

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = self._parse_config(settings, name)
        return config

    def _callback(self, event, **s):
        self.machine.events.post(event, **s)

    def get_express_config(self, value):
        """No express config."""
        raise AssertionError("Not supported")
