"""Plugin config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class PluginPlayer(DeviceConfigPlayer):

    """Base class for a remote ConfigPlayer that is registered as a plug-in to MPF.

    This class is created on the MPF side of things.
    """

    def __init__(self, machine):
        """Initialise plugin player."""
        super().__init__(machine)
        self.bcp_client = None

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
                                        self._initialize_in_mode, priority=20)
        # since bcp is connecting in init_phase_2 we have to postpone this
        self.machine.events.add_handler('init_phase_3',
                                        self._initialise_system_wide)

    def register_player_events(self, config, mode=None, priority=0):
        """Register player events via BCP.

        Override this method in the base class and registers the
        config_player events to send the trigger via BCP instead of calling
        the local play() method.
        """
        event_list = list()
        # when bcp is disabled do not register plugin_player
        if not self.machine.options['bcp']:
            return event_list

        self.bcp_client = self._get_bcp_client(config)

        for event in config:
            event_name, _ = self.machine.events.get_event_and_condition_from_string(event)
            self.machine.bcp.interface.add_registered_trigger_event_for_client(
                self.bcp_client, event_name)
            event_list.append(event_name)

        self.machine.bcp.interface.add_registered_trigger_event_for_client(
            self.bcp_client, '{}_play'.format(self.show_section))
        self.machine.bcp.interface.add_registered_trigger_event_for_client(
            self.bcp_client, '{}_clear'.format(self.show_section))

        return event_list

    def unload_player_events(self, key_list):
        """Unload player events via BCP."""
        for event in key_list:
            self.machine.bcp.interface.remove_registered_trigger_event_for_client(self.bcp_client, event)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Trigger remote player via BCP."""
        self.machine.bcp.interface.bcp_trigger(
            name='{}_play'.format(self.show_section),
            settings=settings, context=context,
            priority=priority)

    def clear_context(self, context):
        """Clear the context at remote player via BCP."""
        self.machine.bcp.interface.bcp_trigger(
            name='{}_clear'.format(self.show_section),
            context=context)
