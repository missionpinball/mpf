"""Base class for asyncio modes."""
import abc
import asyncio

from mpf.core.mode import Mode


class AsyncMode(Mode, metaclass=abc.ABCMeta):

    """Base class for asyncio modes."""

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)

        self._task = None

    def _started(self):
        super()._started()

        self._task = self.machine.clock.loop.create_task(self._run())

    def _stopped(self):
        super()._stopped()

        self._task.cancel()

    @abc.abstractmethod
    @asyncio.coroutine
    def _run(self):
        pass