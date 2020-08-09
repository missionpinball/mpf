"""Queue Relay Config Player."""
from typing import List

from mpf.core.utility_functions import Util

from mpf.core.config_player import ConfigPlayer


class QueueRelayPlayer(ConfigPlayer):

    """Blocks queue events and converts them to normal events."""

    config_file_section = 'queue_relay_player'

    __slots__ = []  # type: List[str]

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Block queue event."""
        del calling_context
        # prevent reposting _from_bcp setting
        kwargs.pop("_from_bcp", None)
        try:
            queue = kwargs.pop('queue')
        except KeyError:
            raise AssertionError(
                "Can only use queue relay player with queue event.")

        instance_dict = self._get_instance_dict(context)

        p = settings['priority']
        if priority:
            p += priority
        handler = self.machine.events.add_handler(settings['wait_for'],
                                                  self._callback, p,
                                                  context=context,
                                                  queue=queue)
        instance_dict[queue] = handler
        queue.wait()
        if settings["pass_args"] and kwargs and settings['args']:
            args = Util.dict_merge(kwargs, settings['args'])
        elif settings["args"]:
            args = settings["args"]
        elif settings["pass_args"]:
            args = kwargs
        else:
            args = {}

        self.machine.events.post(settings['post'], **args)

    def clear_context(self, context):
        """Clear all queues and remove handlers."""
        for queue, handler in self._get_instance_dict(context).items():
            self.machine.events.remove_handler_by_key(handler)
            queue.clear()

        self._reset_instance_dict(context)

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = self._parse_config(settings, name)
        return config

    def _callback(self, queue, context, **kwargs):
        del kwargs
        instance_dict = self._get_instance_dict(context)
        # bail out on error
        if queue not in instance_dict:
            raise AssertionError("Queue {} missing in instance dict: {}.".format(queue, instance_dict))

        self.machine.events.remove_handler_by_key(instance_dict[queue])
        del instance_dict[queue]
        queue.clear()

    def get_express_config(self, value):
        """No express config."""
        raise AssertionError("Not supported")
