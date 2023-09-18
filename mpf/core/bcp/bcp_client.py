"""Base class for all bcp clients."""
import abc

from mpf.core.mpf_controller import MpfController


class BaseBcpClient(MpfController, metaclass=abc.ABCMeta):

    """Base class for bcp clients."""

    __slots__ = ["name", "bcp", "exit_on_close"]

    def __init__(self, machine, name, bcp):
        """initialize client."""
        super().__init__(machine)
        self.name = name
        self.bcp = bcp
        self.exit_on_close = False

    async def connect(self, config):
        """Actively connect client."""
        raise NotImplementedError("implement")

    async def read_message(self):
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
