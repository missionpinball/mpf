"""Plugin config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class PluginPlayer(DeviceConfigPlayer):

    """Base class for a remote ConfigPlayer that is registered as a plug-in to MPF.

    This class is created on the MPF side of things.
    """

    __slots__ = ["bcp_client", "_show_keys"]

    def __init__(self, machine):
        """initialize plugin player."""
        super().__init__(machine)
        self.bcp_client = None
        self._show_keys = {}

    def __repr__(self):
        """Return str representation."""
        return 'PluginPlayer.{}'.format(self.show_section)

    def get_express_config(self, value):
        """Not supported."""
        del value
        raise AssertionError("{} does not support express config".format(self))

    def _get_bcp_client(self, config):
        client_name = config.get('bcp_connection', "local_display")
        client = self.machine.bcp.transport.get_named_client(client_name)
        if not client:
            raise AssertionError(
                "bcp connection {} not found".format(client_name))

        return client

    def _add_handlers(self):
        self.machine.events.add_handler('init_phase_1',
                                        self._initialize_mode_handlers, priority=20)
        # since bcp is connecting in init_phase_2 we have to postpone this
        self.machine.events.add_handler('init_phase_3',
                                        self._initialize_system_wide)

    def register_player_events(self, config, mode=None, priority=0):
        """Register player events via BCP.

        Override this method in the base class and registers the
        config_player events to send the trigger via BCP instead of calling
        the local play() method.
        """
        events = super().register_player_events(config, mode, priority)
        # when bcp is disabled do not register plugin_player
        if self.machine.options['bcp']:
            # getattr check is for IMC to work
            if getattr(self.machine, 'is_shutting_down', False):
                return events
            self.bcp_client = self._get_bcp_client(config)

            self.machine.bcp.interface.add_registered_trigger_event_for_client(
                self.bcp_client, '{}_play'.format(self.show_section))
            self.machine.bcp.interface.add_registered_trigger_event_for_client(
                self.bcp_client, '{}_clear'.format(self.show_section))

        return events

    # pylint: disable-msg=too-many-arguments
    def show_play_callback(self, settings, priority, calling_context, show_tokens, context, start_time):
        """Register BCP events."""
        config = {'bcp_connection': settings['bcp_connection']} if 'bcp_connection' in settings else {}
        event_keys = self.register_player_events(config, None, priority)
        self._show_keys[context + self.config_file_section] = event_keys
        super().show_play_callback(settings, priority, calling_context, show_tokens, context, start_time)

    def show_stop_callback(self, context):
        """Remove BCP events."""
        self.unload_player_events(self._show_keys[context + self.config_file_section])
        del self._show_keys[context + self.config_file_section]
        super().show_stop_callback(context)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Trigger remote player via BCP."""
        self.machine.bcp.interface.bcp_trigger(
            name='{}_play'.format(self.show_section),
            settings=settings, context=context, calling_context=calling_context,
            priority=priority, **kwargs)

    def clear_context(self, context):
        """Clear the context at remote player via BCP."""
        self.machine.bcp.interface.bcp_trigger(
            name='{}_clear'.format(self.show_section),
            context=context)
