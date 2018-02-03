"""Classes which manage BCP transports."""
import asyncio

from typing import Union

from mpf.core.bcp.bcp_client import BaseBcpClient


class BcpTransportManager:

    """Manages BCP transports."""

    def __init__(self, machine):
        """Initialise BCP transport manager."""
        self._machine = machine
        self._transports = []
        self._readers = {}
        self._handlers = {}
        self._machine.events.add_handler("shutdown", self.shutdown)

    def add_handler_to_transport(self, handler, transport: BaseBcpClient):
        """Register client as handler."""
        if handler not in self._handlers:
            self._handlers[handler] = []

        if transport is None:
            raise AssertionError("Cannot register None transport.")

        self._handlers[handler].append(transport)

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
        self._readers[transport].add_done_callback(self._done)

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _receive_loop(self, transport: BaseBcpClient):
        while True:
            try:
                cmd, kwargs = yield from transport.read_message()
            except IOError:
                self.unregister_transport(transport)
                return

            yield from self._machine.bcp.interface.process_bcp_message(cmd, kwargs, transport)

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
            self._machine.stop()

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
        except IOError:
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
