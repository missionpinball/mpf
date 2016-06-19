"""Classes which manage BCP transports."""

class BcpTransportManager:

    """Manages BCP transports."""

    def __init__(self, machine):
        self._machine = machine
        self._transports = []

    def register_transport(self, transport):
        self._transports.append(transport)

    def unregister_transport(self, transport):
        self._transports.remove(transport)

    def get_named_client(self, client_name):
        for client in self._transports:
            if client.name == client_name:
                return client
        else:
            return False

    def send_to_client(self, client, bcp_command, **kwargs):
        try:
            client.send(bcp_command, **kwargs)
        except IOError:
            client.close()
            self.unregister_transport(client)

    def send_to_all_clients(self, bcp_command, **kwargs):
        for client in self._transports:
            self.send_to_client(client, bcp_command, **kwargs)

    def shutdown(self):
        """Prepare the BCP clients for MPF shutdown."""
        for client in self._transports:
            client.close()


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
