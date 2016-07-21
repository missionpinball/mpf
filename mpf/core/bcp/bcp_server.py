"""Bcp server for clients which connect and disconnect randomly."""
import asyncio

from mpf.core.bcp.bcp_socket_client import BCPClientSocket


class BcpServer():

    """Server socket which listens for incoming BCP clients."""

    def __init__(self, machine):
        self.machine = machine
        self._server = None

    @asyncio.coroutine
    def start(self):
        """Start the server."""
        self._server = yield from self.machine.clock.start_server(
            self._accept_client, '127.0.0.1', 5051, loop=self.machine.clock.loop)

    @asyncio.coroutine
    def stop(self, loop):
        """Stop the BCP server, i.e. closes the listening socket(s)."""
        if self.server:
            self.server.close()
            yield from self.server.wait_closed()

        self.server = None

    @asyncio.coroutine
    def _accept_client(self, client_reader, client_writer):
        """Accept an connection and create client."""
        client = BCPClientSocket(self.machine, None, self.machine.bcp.interface)
        client.accept_connection(client_reader, client_writer)
        self.machine.bcp.transport.register_transport(client)
