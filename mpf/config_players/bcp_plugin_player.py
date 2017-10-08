"""Plugin config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class BcpPluginPlayer(DeviceConfigPlayer):

    """Base class for a remote ConfigPlayer that is registered as a plug-in to MPF.

    This class is created on the MPF side of things.
    """

    def __init__(self, machine):
        """Initialise plugin player."""
        super().__init__(machine)
        self.bcp_client = None

    def __repr__(self):
        """Return str representation."""
        return 'BcpPluginPlayer.{}'.format(self.show_section)

    def _get_bcp_client(self, config):
        client_name = config.get('bcp_connection', "local_display")
        client = self.machine.bcp.transport.get_named_client(client_name)
        if not client:
            raise AssertionError("bcp connection {} not found".format(client_name))

        return client

    def _add_handlers(self):
        self.machine.events.add_handler('init_phase_1', self._initialize_in_mode, priority=20)
        # since bcp is connecting in init_phase_2 we have to postpone this
        self.machine.events.add_handler('init_phase_3', self._initialise_system_wide)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Trigger remote player via BCP."""
        context_dics = self._get_instance_dict(context)

        for element, s in settings.items():
            client = self._get_bcp_client(s)
            context_dics[element] = client
            self.machine.bcp.interface.bcp_trigger_client(
                client=client,
                name='{}_play'.format(self.show_section),
                element=element,
                settings=s,
                calling_context=calling_context,
                context=context,
                priority=priority)

    def clear_context(self, context):
        """Clear the context at remote player via BCP."""
        context_dics = self._get_instance_dict(context)
        for element, client in context_dics.items():
            self.machine.bcp.interface.bcp_trigger_client(
                client=client,
                element=element,
                name='{}_clear'.format(self.show_section),
                context=context)

    def get_express_config(self, value):
        """Raise error."""
        raise AssertionError("Express config not implemented.")
