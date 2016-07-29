"""Base class for all bcp clients."""
import abc


class BaseBcpClient(metaclass=abc.ABCMeta):

    """Base class for bcp clients."""

    def __init__(self, machine, name, bcp):
        """Initialise client."""
        self.name = name
        self.machine = machine
        self.bcp = bcp

    def connect(self, config):
        """Actively connect client."""
        raise NotImplementedError("implement")

    def accept_connection(self, receiver, sender):
        """Created client for incoming connection."""
        raise NotImplementedError("implement")

    def send(self, bcp_command, kwargs):
        """Send data to client."""
        raise NotImplementedError("implement")

    def stop(self):
        """Stop client connection."""
        raise NotImplementedError("implement")
