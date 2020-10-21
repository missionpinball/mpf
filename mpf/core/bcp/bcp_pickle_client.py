"""BCP pickle client."""
import asyncio
import pickle
import struct

from mpf.core.bcp.bcp_client import BaseBcpClient


class BcpPickleClient(BaseBcpClient):

    """BCP client using pickle."""

    def __init__(self, machine, name, bcp):
        """Initialise BCP pickle client."""
        super().__init__(machine, name, bcp)
        self._receiver = None
        self._sender = None

    async def read_message(self):
        """Read the next message."""
        message_length = struct.unpack("!I", (await self._receiver.readexactly(4)))[0]
        message_raw = await self._receiver.readexactly(message_length)

        return pickle.load(message_raw)

    async def connect(self, config):
        """Actively connect to server."""
        config = self.machine.config_validator.validate_config(
            'bcp:connections', config, 'bcp:connections')

        self.info_log("Connecting BCP to '%s' at %s:%s...",
                      self.name, config['host'], config['port'])

        while True:
            connector = self.machine.clock.open_connection(config['host'], config['port'])
            try:
                self._receiver, self._sender = await connector
            except (ConnectionRefusedError, OSError):
                if config.get('required'):
                    await asyncio.sleep(.1)
                    continue

                self.info_log("No BCP connection made to '%s' %s:%s",
                              self.name, config['host'], config['port'])
                return False
            break

        self.info_log("Connected BCP to '%s' %s:%s", self.name, config['host'], config['port'])
        return True

    def accept_connection(self, receiver, sender):
        """Create client for incoming connection."""
        self._receiver = receiver
        self._sender = sender

    def send(self, bcp_command, kwargs):
        """Send message."""
        message_raw = pickle.dump(bcp_command, kwargs)
        complete_message = struct.pack("!I", len(message_raw)) + message_raw

        if hasattr(self._sender.transport, "is_closing") and self._sender.transport.is_closing():
            self.warning_log("Failed to write to bcp since transport is closing. Transport %s", self._sender.transport)
            return
        self._sender.write(complete_message)

    def stop(self):
        """Stop client."""
        self.debug_log("Stopping socket client")
        self._sender.close()
