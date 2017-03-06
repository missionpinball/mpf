"""Queue Relay Config Player."""
from mpf.core.config_player import ConfigPlayer


class QueueRelayPlayer(ConfigPlayer):

    """Blocks queue events and converts them to normal events."""

    config_file_section = 'queue_relay_player'
    show_section = None
    device_collection = None

    def play(self, settings, context, priority=0, **kwargs):
        """Block queue event."""
        try:
            queue = kwargs['queue']
        except KeyError:
            raise AssertionError("Can only use queue relay player with queue event.")

        instance_dict = self._get_instance_dict(context)

        p = settings['priority']
        if priority:
            p += priority
        handler = self.machine.events.add_handler(settings['wait_for'], self._callback, p, context=context, queue=queue)
        instance_dict[queue] = handler
        queue.wait()

        self.machine.events.post(settings['post'], **settings['args'])

    def clear_context(self, context):
        """Clear all queues."""
        for queue in self._get_instance_dict(context):
            queue.clear()

        self._reset_instance_dict(context)

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = self._parse_config(settings, name)
        return config

    def _callback(self, queue, context, **kwargs):
        del kwargs
        instance_dict = self._get_instance_dict(context)
        self.machine.events.remove_handler_by_key(instance_dict[queue])
        del instance_dict[queue]
        queue.clear()

    def get_express_config(self, value):
        """No express config."""
        raise AssertionError("Not supported")


player_cls = QueueRelayPlayer
