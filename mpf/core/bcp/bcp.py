"""BCP module."""
from mpf.core.mpf_controller import MpfController

from mpf.core.bcp.bcp_server import BcpServer
from mpf.core.utility_functions import Util

from mpf.core.bcp.bcp_interface import BcpInterface
from mpf.core.bcp.bcp_transport import BcpTransportManager


class Bcp(MpfController):

    """BCP Module."""

    def __init__(self, machine):
        """Initialise BCP module."""
        super().__init__(machine)
        self.interface = BcpInterface(machine)
        self.transport = BcpTransportManager(machine)
        self.servers = []

        if not self.machine.options['bcp']:
            return

        self.machine.events.add_handler('init_phase_2',
                                        self._setup_bcp_connections)

        self.machine.events.add_handler('init_phase_4',
                                        self._setup_bcp_servers)

        self.machine.events.add_handler('shutdown',
                                        self._stop_servers)


    def send(self, bcp_command, **kwargs):
        """Emulate legacy send.

        Args:
            bcp_command: Commmand to send
        """
        self.transport.send_to_all_clients(bcp_command, **kwargs)

    def _setup_bcp_connections(self):
        """Connect to BCP servers from MPF config."""
        if 'connections' not in self.machine.config['bcp'] or not self.machine.config['bcp']['connections']:
            return

        for name, settings in self.machine.config['bcp']['connections'].items():
            client = Util.string_to_class(settings['type'])(self.machine, name, self.machine.bcp)
            client.connect(settings)
            client.exit_on_close = True
            self.transport.register_transport(client)

    def _setup_bcp_servers(self):
        """Start BCP servers to allow other clients to connect."""
        if 'servers' not in self.machine.config['bcp'] or not self.machine.config['bcp']['servers']:
            return

        for settings in self.machine.config['bcp']['servers'].values():
            server = BcpServer(self.machine, settings['ip'], settings['port'], settings['type'])
            self.machine.clock.loop.run_until_complete(server.start())
            self.servers.append(server)

    def _stop_servers(self):
        """Stop BCP servers."""
        for server in self.servers:
            server.stop()
