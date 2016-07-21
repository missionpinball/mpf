"""BCP module."""
from mpf.core.bcp.bcp_server import BcpServer
from mpf.core.utility_functions import Util

from mpf.core.bcp.bcp_interface import BcpInterface
from mpf.core.bcp.bcp_transport import BcpTransportManager


class Bcp:

    """BCP Module."""

    def __init__(self, machine):
        self.interface = BcpInterface(machine)
        self.transport = BcpTransportManager(machine)
        self.machine = machine

        self.machine.events.add_handler('init_phase_2',
                                        self._setup_bcp_connections)

        self.machine.events.add_handler('init_phase_4',
                                        self._setup_bcp_server)

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
            self.transport.register_transport(client)

    def _setup_bcp_server(self):
        """Start an BCP server to allow other clients to connect."""
        self.server = BcpServer(self.machine)
        self.machine.clock.loop.run_until_complete(self.server.start())
