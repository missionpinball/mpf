import asyncio

from mpf.core.bcp.bcp_client import BaseBcpClient
from mpf.tests.MpfTestCase import MpfTestCase


class MockBcpClient(BaseBcpClient):

    """A Mock BCP Client.

    This is used in tests require BCP for testing but where you don't actually
    create a real BCP connection.

    """

    def __init__(self, machine, name, bcp):

        self.module_name = "BCPClient"
        self.config_name = "bcp_client"

        super().__init__(machine, name, bcp)
        self.name = name
        self.receive_queue = asyncio.Queue(loop=self.machine.clock.loop)
        self.send_queue = asyncio.Queue(loop=self.machine.clock.loop)

    @asyncio.coroutine
    def connect(self, config):
        return

    @asyncio.coroutine
    def read_message(self):
        obj = yield from self.receive_queue.get()
        return obj

    def accept_connection(self, receiver, sender):
        pass

    def send(self, bcp_command, bcp_command_args):
        if bcp_command == "reset":
            self.receive_queue.put_nowait(("reset_complete", {}))
            return
        if bcp_command == "error":
            raise AssertionError("Got bcp error")
        self.send_queue.put_nowait((bcp_command, bcp_command_args))

    def stop(self):
        pass


class MockExternalBcpClient(BaseBcpClient):

    """Connected BCP instance."""

    def __init__(self, mock_bcp_client):
        """Initialise virtual external bcp client."""
        self.module_name = "BCPClient"
        self.config_name = "bcp_client"
        super().__init__(mock_bcp_client.machine, mock_bcp_client.name, mock_bcp_client.bcp)
        self.mock_bcp_client = mock_bcp_client  # type: MockBcpClient

    def send(self, bcp_command, kwargs):
        """Send to mock."""
        self.mock_bcp_client.receive_queue.put_nowait((bcp_command, kwargs))

    @asyncio.coroutine
    def connect(self, config):
        """Do not call."""
        raise AssertionError("Do not call")

    def accept_connection(self, receiver, sender):
        """Do not call."""
        raise AssertionError("Do not call")

    def read_message(self):
        """Read from mock client."""
        return self.mock_bcp_client.send_queue.get()

    @asyncio.coroutine
    def wait_for_response(self, bcp_command):
        """Wait for a command and ignore all others."""
        while True:
            cmd, args = yield from self.read_message()
            if cmd == "reset":
                self.send("reset_complete", {})
                continue
            if cmd == bcp_command:
                return cmd, args

    def reset_and_return_queue(self):
        """Clear queue."""
        queue = []
        while not self.mock_bcp_client.send_queue.empty():
            queue.append(self.mock_bcp_client.send_queue.get_nowait())

        return queue

    def stop(self):
        """Do not call."""
        pass


class MpfBcpTestCase(MpfTestCase):

    """An MpfTestCase instance which uses the MockBcpClient."""

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self._bcp_client = None             # type: MockBcpClient
        self._bcp_external_client = None    # type: MockExternalBcpClient

        # use bcp mock
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.tests.MpfBcpTestCase.MockBcpClient"}}, "servers": []}

    def get_use_bcp(self):
        return True

    def setUp(self):
        super().setUp()
        self._bcp_client = self.machine.bcp.transport.get_named_client("local_display")
        self._bcp_external_client = MockExternalBcpClient(self._bcp_client)
