"""A show queue which can will be played sequentially."""
from collections import deque

from mpf.assets.show import RunningShow, ShowConfig
from mpf.core.system_wide_device import SystemWideDevice

MYPY = False
if MYPY:   # pragma: no cover
    from typing import Tuple, Deque, Optional


class ShowQueue(SystemWideDevice):

    """Represents a show queue."""

    config_section = 'show_queues'
    collection = 'show_queues'
    class_label = 'show_queue'

    __slots__ = ["shows_queue", "_current_show"]

    def __init__(self, machine, name):
        """initialize show queue."""
        super().__init__(machine, name)

        self.shows_queue = deque()  # type: Deque[Tuple[ShowConfig, int]]
        self._current_show = None   # type: Optional[RunningShow]

    def enqueue_show(self, show_config: ShowConfig, start_step: int):
        """Add a show to the end of the queue."""
        self.shows_queue.append((show_config, start_step))
        if not self._current_show:
            self._play_next_show()

    def _play_next_show(self):
        """Play the next show."""
        if not self.shows_queue:
            # no show queued
            self._current_show = None
            return

        show_config, start_step = self.shows_queue.popleft()
        self._current_show = self.machine.show_controller.replace_or_advance_show(self._current_show, show_config,
                                                                                  start_step=start_step,
                                                                                  stop_callback=self._play_next_show)
