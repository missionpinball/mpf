"""Base class for ball device handlers."""
import asyncio

from mpf.core.utility_functions import Util


class BallDeviceStateHandler:

    """Base class for ball device handler."""

    __slots__ = ["ball_device", "machine", "_task"]

    def __init__(self, ball_device):
        """initialize handler.

        Args:
        ----
            ball_device(mpf.devices.ball_device.ball_device.BallDevice): parent ball device
        """
        self.ball_device = ball_device
        self.machine = ball_device.machine
        self._task = None

    def stop(self):
        """Stop handler."""
        if self._task:
            self._task.cancel()
            try:
                self.machine.clock.loop.run_until_complete(self._task)
            except asyncio.CancelledError:
                pass

    def debug_log(self, *args, **kwargs):
        """Debug log."""
        self.ball_device.debug_log(*args, **kwargs)

    def info_log(self, *args, **kwargs):
        """Info log."""
        self.ball_device.info_log(*args, **kwargs)

    def warning_log(self, *args, **kwargs):
        """Warning log."""
        self.ball_device.warning_log(*args, **kwargs)

    async def initialize(self):
        """initialize handler."""
        self._task = asyncio.create_task(self._run())
        self._task.add_done_callback(Util.raise_exceptions)

    async def _run(self):
        raise NotImplementedError()
