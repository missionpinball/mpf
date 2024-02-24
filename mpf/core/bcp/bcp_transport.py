"""Classes which manage BCP transports."""
from collections import defaultdict

from typing import Union

from mpf.core.bcp.bcp_client import BaseBcpClient
from mpf.core.utility_functions import Util

MYPY = False  # noqa
if MYPY:
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class BcpTransportManager:

    """Manages BCP transports."""

    __slots__ = ["_machine", "_transports", "_readers", "_handlers"]

    def __init__(self, machine):
        """initialize BCP transport manager."""
        self._machine = machine     # type: MachineController
        self._transports = []
        self._readers = {}
        self._handlers = defaultdict(set)
        self._machine.events.add_handler("shutdown", self.shutdown)

    def add_handler_to_transport(self, handler, transport: BaseBcpClient):
        """Register client as handler."""
        if transport is None:
            raise AssertionError("Cannot register None transport.")

        self._handlers[handler].add(transport)

    def remove_transport_from_handle(self, handler, transport: BaseBcpClient):
        """Remove client from a certain handler."""
        if transport in self._handlers[handler]:
            self._handlers[handler].remove(transport)

    def get_transports_for_handler(self, handler):
        """Get clients which registered for a certain handler."""
        return self._handlers.get(handler, [])

    def register_transport(self, transport, future=None, **kwargs):
        """Register a client."""
        del future
        del kwargs
        self._transports.append(transport)
        self._readers[transport] = self._machine.clock.loop.create_task(self._receive_loop(transport))
        self._readers[transport].add_done_callback(Util.raise_exceptions)

    async def _receive_loop(self, transport: BaseBcpClient):
        while True:
            try:
                cmd, kwargs = await transport.read_message()
            except OSError:
                self.unregister_transport(transport)
                return

            await self._machine.bcp.interface.process_bcp_message(cmd, kwargs, transport)

    def unregister_transport(self, transport: BaseBcpClient):
        """Unregister client."""
        if transport in self._transports:
            self._transports.remove(transport)

        # remove transport from all handlers
        for handler in self._handlers:
            if transport in self._handlers[handler]:
                self._handlers[handler].remove(transport)

        if transport in self._readers:
            self._readers[transport].cancel()
            del self._readers[transport]

        if transport.exit_on_close:
            self._machine.stop("BCP client {} disconnected and exit_on_close is set".format(transport.name))

    def get_all_clients(self):
        """Get a list of all clients."""
        return self._transports

    def get_named_client(self, client_name) -> Union[BaseBcpClient, bool]:
        """Get a client by name."""
        for client in self._transports:
            if client.name == client_name:
                return client
        return False

    def send_to_clients(self, clients, bcp_command, **kwargs):
        """Send command to a list of clients."""
        for client in set(clients):
            self.send_to_client(client, bcp_command, **kwargs)

    def send_to_clients_with_handler(self, handler, bcp_command, **kwargs):
        """Send command to clients which registered for a specific handler."""
        clients = self.get_transports_for_handler(handler)
        self.send_to_clients(clients, bcp_command, **kwargs)

    def send_to_client(self, client: BaseBcpClient, bcp_command, **kwargs):
        """Send command to a specific bcp client."""
        try:
            client.send(bcp_command, kwargs)
        except OSError:
            client.stop()
            self.unregister_transport(client)

    def send_to_all_clients(self, bcp_command, **kwargs):
        """Send command to all bcp clients."""
        for client in self._transports:
            self.send_to_client(client, bcp_command, **kwargs)

    def shutdown(self, **kwargs):
        """Prepare the BCP clients for MPF shutdown."""
        del kwargs
        for client in list(self._transports):
            client.stop()
            self.unregister_transport(client)
