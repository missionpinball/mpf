"""Classes which manage BCP transports."""

class BcpTransportManager:

    """Manages BCP transports."""

    def __init__(self, machine):
        self._machine = machine
        self._transports = []
        self._handlers = {}

    def add_handler_to_transport(self, handler, transport):
        if handler not in self._handlers:
            self._handlers[handler] = []

        if transport not in self._handlers[handler]:
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
        for client in clients:
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


class BcpTransport:

    """Baseclass for BCP transports."""

    def __init__(self, transport_manager, bcp_handler):
        self._transport_manager = transport_manager
        self._bcp_handler = bcp_handler
        self._disconnect_callbacks = []
        self.name = None

    def send(self, bcp_command, **kwargs):
        raise NotImplementedError()

    def add_disconnect_callback(self, callback):
        self._disconnect_callbacks.append(callback)

    def close(self):
        for callback in self._disconnect_callbacks:
            callback(self)
