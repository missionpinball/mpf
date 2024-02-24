"""Bcp server for clients which connect and disconnect randomly."""
import asyncio

from mpf.exceptions.runtime_error import MpfRuntimeError

from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController


class BcpServer(MpfController):

    """Server socket which listens for incoming BCP clients."""

    config_name = "bcp_server"

    def __init__(self, machine, ip, port, server_type):
        """initialize BCP server."""
        super().__init__(machine)
        self._server = None
        self._ip = ip
        self._port = port
        self._type = server_type

    async def start(self):
        """Start the server."""
        try:
            self._server = await self.machine.clock.start_server(
                self._accept_client, self._ip, self._port)
        except OSError as e:
            raise MpfRuntimeError("Failed to bind BCP Socket to {} on port {}. "
                                  "Is there another application running on that port?".format(self._ip, self._port), 1,
                                  "MPF BCP Server") from e

    def stop(self):
        """Stop the BCP server, i.e. closes the listening socket(s)."""
        if self._server:
            self._server.close()

        self._server = None

    async def _accept_client(self, client_reader, client_writer):
        """Accept an connection and create client."""
        self.info_log("New client connected.")
        client = Util.string_to_class(self._type)(self.machine, None, self.machine.bcp)
        client.accept_connection(client_reader, client_writer)
        client.exit_on_close = False
        self.machine.bcp.transport.register_transport(client)
