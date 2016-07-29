"""Classes which manage BCP transports."""


class BcpTransportManager:

    """Manages BCP transports."""

    def __init__(self, machine):
        self._machine = machine
        self._transports = []
        self._handlers = {}
        self._machine.events.add_handler("shutdown", self.shutdown)

    def add_handler_to_transport(self, handler, transport):
        if handler not in self._handlers:
            self._handlers[handler] = []

        self._handlers[handler].append(transport)

    def remove_transport_from_handle(self, handler, transport):
        self._handlers[handler].remove(transport)

    def get_transports_for_handler(self, handler):
        return self._handlers.get(handler, [])

    def register_transport(self, transport):
        self._transports.append(transport)

    def unregister_transport(self, transport):
        self._transports.remove(transport)

        # remove transport from all handlers
        for handler in self._handlers:
            self._handlers[handler].remove(transport)

    def get_named_client(self, client_name):
        for client in self._transports:
            if client.name == client_name:
                return client
        else:
            return False

    def send_to_clients(self, clients, bcp_command, **kwargs):
        for client in set(clients):
            self.send_to_client(client, bcp_command, **kwargs)

    def send_to_clients_with_handler(self, handler, bcp_command, **kwargs):
        clients = self.get_transports_for_handler(handler)
        self.send_to_clients(clients, bcp_command, **kwargs)

    def send_to_client(self, client, bcp_command, **kwargs):
        try:
            client.send(bcp_command, kwargs)
        except IOError:
            client.stop()
            self.unregister_transport(client)

    def send_to_all_clients(self, bcp_command, **kwargs):
        for client in self._transports:
            self.send_to_client(client, bcp_command, **kwargs)

    def shutdown(self):
        """Prepare the BCP clients for MPF shutdown."""
        for client in self._transports:
            client.stop()
