"""Base class for all bcp clients."""
import abc

import asyncio

from mpf.core.mpf_controller import MpfController


class BaseBcpClient(MpfController, metaclass=abc.ABCMeta):

    """Base class for bcp clients."""

    def __init__(self, machine, name, bcp):
        """Initialise client."""
        super().__init__(machine)
        self.name = name
        self.bcp = bcp
        self.exit_on_close = False

    @asyncio.coroutine
    def connect(self, config):
        """Actively connect client."""
        raise NotImplementedError("implement")

    @asyncio.coroutine
    def read_message(self):
        """Read one message from client."""
        raise NotImplementedError("implement")

    def accept_connection(self, receiver, sender):
        """Handle incoming connection from remote client."""
        raise NotImplementedError("implement")

    def send(self, bcp_command, kwargs):
        """Send data to client."""
        raise NotImplementedError("implement")

    def stop(self):
        """Stop client connection."""
        raise NotImplementedError("implement")
