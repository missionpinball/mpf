"""BCP module."""
from mpf.core.bcp.bcp_interface import BcpInterface
from mpf.core.bcp.bcp_socket_client import BCPClientSocket
from mpf.core.bcp.bcp_transport import BcpTransportManager


class Bcp:
    def __init__(self, machine):
        self.interface = BcpInterface(machine)
        self.transport = BcpTransportManager(machine)
        self.machine = machine

        self.machine.events.add_handler('init_phase_2',
                                        self._setup_bcp_connections)

    def send(self, bcp_command, **kwargs):
        """Emulate legacy send."""
        self.transport.send_to_all_clients(bcp_command, **kwargs)

    def _setup_bcp_connections(self):
        """Connect to BCP servers from MPF config."""
        if 'connections' not in self.machine.config['bcp'] or not self.machine.config['bcp']['connections']:
            return

        for name, settings in self.machine.config['bcp']['connections'].items():
            if 'host' not in settings:
                break

            client = BCPClientSocket(self.machine, name, settings, self.machine.bcp)
            self.transport.register_transport(client)
            self.interface.bcp_client_connected(client)
