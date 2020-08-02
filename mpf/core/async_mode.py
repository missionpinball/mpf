"""Base class for asyncio modes."""
from typing import Optional

import abc
import asyncio

from mpf.core.mode import Mode

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class AsyncMode(Mode, metaclass=abc.ABCMeta):

    """Base class for asyncio modes."""

    __slots__ = ["_task"]

    def __init__(self, machine: "MachineController", *args, **kwargs) -> None:
        """Initialise async mode."""
        super().__init__(machine, *args, **kwargs)

        self._task = None   # type: Optional[asyncio.Task]

    def _started(self, **kwargs) -> None:
        """Start main task."""
        del kwargs
        super()._started()

        self._task = self.machine.clock.loop.create_task(self._run())
        self._task.add_done_callback(self._mode_ended)

    def _mode_ended(self, future: asyncio.Future) -> None:
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        try:
            future.result()
        except asyncio.CancelledError:
            pass

        # stop mode
        self.stop()

    def _stopped(self) -> None:
        """Cancel task."""
        super()._stopped()

        if self._task:
            self._task.cancel()
            self._task = None

    @abc.abstractmethod
    async def _run(self) -> None:
        """Start main task which runs as long as the mode is active.

        Overwrite this function in your mode.

        Its automatically canceled when the mode stops. You can catch CancelError to handle mode stop.
        """
