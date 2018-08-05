"""Base class for ball device handlers."""
import asyncio


class BallDeviceStateHandler:

    """Base class for ball device handler."""

    __slots__ = ["ball_device", "machine", "_task"]

    def __init__(self, ball_device):
        """Initialise handler.

        Args:
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

    @asyncio.coroutine
    def initialise(self):
        """Initialise handler."""
        self._task = self.machine.clock.loop.create_task(self._run())
        self._task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _run(self):
        raise NotImplementedError()
