"""MPF Hardware Service for VPE.

This is separated from the platform because we need to catch a syntax error in python 3.5 and earlier.
"""
import asyncio
from mpf.platforms.visual_pinball_engine import platform_pb2_grpc
from mpf.platforms.visual_pinball_engine import platform_pb2


class MpfHardwareService(platform_pb2_grpc.MpfHardwareServiceServicer):

    """MPF Service for VPE."""

    def __init__(self, machine):
        """Initialise MPF service for VPE."""
        self._connected = asyncio.Future()
        self.machine = machine
        self.switch_queue = asyncio.Queue()
        self.command_queue = asyncio.Queue()

    def send_command(self, command):
        """Send command to VPE."""
        self.command_queue.put_nowait(command)

    def get_switch_queue(self):
        """Return switch queue."""
        return self.switch_queue

    async def wait_for_vpe_connect(self):
        """Wait until VPE has connected."""
        return await self._connected

    async def Start(self, request, context):    # noqa
        """Start MPF."""
        self._connected.set_result(request)
        while True:
            command = await self.command_queue.get()
            # this only works in Python 3.6+
            yield command

    async def SendSwitchChanges(self, request_iterator, context):   # noqa
        """Process a stream of switches."""
        async for element in request_iterator:
            self.switch_queue.put_nowait(element)

        return platform_pb2.EmptyResponse()

    async def Quit(self, request, context):     # noqa
        """Stop MPF."""
        self.machine.stop(reason="VPE exited.")
        return platform_pb2.EmptyResponse()
