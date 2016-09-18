import asyncio

from mpf.core.bcp.bcp_client import BaseBcpClient
from mpf.tests.MpfTestCase import MpfTestCase


class MockBcpClient(BaseBcpClient):
    def __init__(self, machine, name, bcp):
        super().__init__(machine, name, bcp)
        self.name = name
        self.receive_queue = asyncio.Queue(loop=self.machine.clock.loop)
        self.send_queue = []

    def connect(self, config):
        pass

    @asyncio.coroutine
    def read_message(self):
        obj = yield from self.receive_queue.get()
        return obj

    def accept_connection(self, receiver, sender):
        pass

    def send(self, bcp_command, bcp_command_args):
        if bcp_command == "error":
            raise AssertionError("Got bcp error")
        self.send_queue.append((bcp_command, bcp_command_args))

    def stop(self):
        pass


class MpfBcpTestCase(MpfTestCase):

    """MpfTestCase with mocked BCP."""

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

        # use bcp mock
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.tests.MpfBcpTestCase.MockBcpClient"}}, "servers": []}

    def get_use_bcp(self):
        return True

    def setUp(self):
        super().setUp()
        self._bcp_client = self.machine.bcp.transport.get_named_client("local_display")