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

    # pylint: disable-msg=too-many-arguments
    def show_play_callback(self, settings, priority, calling_context, show_tokens, context, start_time):
        """Add bcp context dict."""
        bcp_context = context + "_bcp"
        if bcp_context not in self.instances:
            self.instances[bcp_context] = dict()

        if self.config_file_section not in self.instances[bcp_context]:
            self.instances[bcp_context][self.config_file_section] = dict()
        super().show_play_callback(settings, priority, calling_context, show_tokens, context, start_time)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Trigger remote player via BCP."""
        context_dict = self._get_instance_dict(context + "_bcp")

        if not self.machine.options['bcp']:
            return

        for element, s in settings.items():
            client = self._get_bcp_client(s)
            context_dict[element] = client
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
        context_dict = self._get_instance_dict(context + "_bcp")
        for element, client in context_dict.items():
            self.machine.bcp.interface.bcp_trigger_client(
                client=client,
                element=element,
                name='{}_clear'.format(self.show_section),
                context=context)
        self._reset_instance_dict(context + "_bcp")

    def get_express_config(self, value):
        """Raise error."""
        raise AssertionError("Express config not implemented.")
