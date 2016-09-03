"""Base class for asyncio modes."""
import abc
import asyncio

from mpf.core.mode import Mode


class AsyncMode(Mode, metaclass=abc.ABCMeta):

    """Base class for asyncio modes."""

    def __init__(self, machine, config, name, path):
        """Initialise async mode."""
        super().__init__(machine, config, name, path)

        self._task = None

    def _started(self):
        """Start main task."""
        super()._started()

        self._task = self.machine.clock.loop.create_task(self._run())
        self._task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    def _stopped(self):
        """Cancel task."""
        super()._stopped()

        self._task.cancel()

    @abc.abstractmethod
    @asyncio.coroutine
    def _run(self):
        """Main task which runs as long as the mode is active.

        Overwrite this function in your mode.

        Its automatically canceled when the mode stops. You can catch CancelError to handle mode stop.
        """
        pass
