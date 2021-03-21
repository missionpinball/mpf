"""Baseclass for ball device ball counters.

The duty of this device is to maintain the current ball count of the device.
"""
import asyncio

from typing import List, Optional
from mpf.core.utility_functions import Util

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.devices.ball_device.ball_device import BallDevice  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.ball_device.ball_count_handler import BallCountHandler     # pylint: disable-msg=cyclic-import,unused-import; # noqa


class EjectTracker:

    """Tracks ball changes during an eject."""

    __slots__ = ["machine", "_already_left", "_ball_count_handler", "_task", "_event_queue", "_ball_left",
                 "_ball_returned", "_ready", "_unknown_balls", "_num_unknown_balls", "_num_lost_balls"]

    def __init__(self, ball_counter_handler, already_left):
        """Initialise eject tracker."""
        self.machine = ball_counter_handler.machine
        self._already_left = already_left
        self._ball_count_handler = ball_counter_handler     # type: BallCountHandler
        self._task = None
        self._event_queue = asyncio.Queue()
        self._ball_left = asyncio.Future()
        self._ball_returned = asyncio.Future()
        self._ready = asyncio.Future()
        self._unknown_balls = asyncio.Future()
        self._num_unknown_balls = 0
        self._num_lost_balls = 0

    async def will_eject(self):
        """Start process."""
        await self._ball_count_handler.counter.wait_for_count_stable()
        ball_changes = self._ball_count_handler.counter.register_change_stream()
        if not self._already_left:
            ball_left = await self._ball_count_handler.counter.wait_for_ball_to_leave()
            self._ball_left = asyncio.ensure_future(ball_left)

        self._task = self.machine.clock.loop.create_task(self._run(ball_changes))
        self._task.add_done_callback(Util.raise_exceptions)

    async def _run(self, ball_changes):
        already_left = self._already_left
        while True:
            change = await ball_changes.get()
            if isinstance(change, BallLostActivity) and not already_left and self._ball_left.done():
                already_left = True
                self._ball_count_handler.ball_device.debug_log("Got ball left during eject")
                continue

            if isinstance(change, BallLostActivity):
                self.track_lost_balls(1)
            elif isinstance(change, BallEntranceActivity):
                await self.track_ball_entrance()
            elif isinstance(change, UnknownBallActivity):
                self.track_unknown_balls(1)
            elif isinstance(change, BallReturnActivity):
                self.track_ball_returned()
            else:
                raise AssertionError("Unknown activity {}".format(change))

    def cancel(self):
        """Cancel eject tracker."""
        if self._task:
            self._task.cancel()
        if not self._ball_left.done():
            self._ball_left.cancel()

    def is_jammed(self):
        """Return true if currently jammed."""
        return self._ball_count_handler.counter.is_jammed()

    def track_ball_returned(self):
        """Track ball returned."""
        self._ball_count_handler.ball_device.debug_log("Got ball return during eject")
        self._ball_returned.set_result(True)

    async def track_ball_entrance(self):
        """Track ball entrance."""
        self._ball_count_handler.ball_device.debug_log("Got ball entrance during eject")
        await self._ball_count_handler.entrance_during_eject()

    def track_unknown_balls(self, balls):
        """Track unknown ball."""
        self._ball_count_handler.ball_device.debug_log("Got %s unknown ball during eject", balls)
        self._num_unknown_balls += balls
        if not self._unknown_balls.done():
            self._unknown_balls.set_result(True)

    def get_num_unknown_balls(self):
        """Return unknown balls."""
        return self._num_unknown_balls

    def track_lost_balls(self, balls):
        """Track lost ball."""
        self._num_lost_balls += balls
        if self._num_lost_balls >= self._num_unknown_balls and self._unknown_balls.done():
            self._unknown_balls = asyncio.Future()

    def wait_for_ball_return(self):
        """Wait until a ball returned."""
        return asyncio.shield(self._ball_returned)

    def wait_for_ball_unknown_ball(self):
        """Return true if the device has unknown balls which are neither clearly new or returned."""
        return asyncio.shield(self._unknown_balls)

    def wait_for_ball_left(self):
        """Wait until a ball left."""
        if self._already_left:
            raise AssertionError("Invalid wait. Ball left before eject.")
        return asyncio.shield(self._ball_left)

    def wait_for_ready(self):
        """Wait until the device is ready."""
        return asyncio.shield(self._ready)

    def set_ready(self):
        """Set device ready."""
        self._ready.set_result("ready")


class BallActivity:

    """An acticity in a ball device."""

    __slots__ = []  # type: List[str]


class BallLostActivity(BallActivity):

    """A ball was lost/ejected from device."""

    __slots__ = []  # type: List[str]


class NewBallActivity(BallActivity):

    """A new ball was found in the device."""

    __slots__ = []  # type: List[str]


class BallEntranceActivity(NewBallActivity):

    """A new ball entered the device (did not return)."""

    __slots__ = []  # type: List[str]


class BallReturnActivity(NewBallActivity):

    """A ball returned."""

    __slots__ = []  # type: List[str]


class UnknownBallActivity(NewBallActivity):

    """A unknown new ball was found in the device.

    This could be a returned or entered ball.
    """

    __slots__ = []  # type: List[str]


class PhysicalBallCounter:

    """Ball counter for ball device."""

    __slots__ = ["ball_device", "config", "machine", "_last_count", "_count_stable", "_activity_queues",
                 "_ball_change_futures"]

    def __init__(self, ball_device, config) -> None:
        """Initialise ball counter."""
        self.ball_device = ball_device              # type: BallDevice
        self.config = config
        self.machine = self.ball_device.machine     # type: MachineController

        self._last_count = None                     # type: Optional[int]
        self._count_stable = asyncio.Event()
        self._activity_queues = []                  # type: List[asyncio.Queue[BallActivity]]
        self._ball_change_futures = []              # type: List[asyncio.Future]

    def stop(self):
        """Stop counter."""

    def invalidate_count(self):
        """Invalidate the count."""
        self._count_stable.clear()

    def mark_count_as_stable_and_trigger_activity(self):
        """Mark count as stable and trigger activity."""
        self._count_stable.set()
        self.trigger_activity()

    def trigger_activity(self):
        """Trigger all activity futures."""
        for future in self._ball_change_futures:
            if not future.done():
                future.set_result(True)
        self._ball_change_futures = []

    def debug_log(self, *args, **kwargs):
        """Debug log."""
        self.ball_device.debug_log(*args, **kwargs)

    def count_balls_sync(self) -> int:
        """Return the number of current active switches or raises ValueError when count is not stable."""
        raise NotImplementedError()

    def is_jammed(self) -> bool:
        """Return true if device is jammed."""
        raise NotImplementedError()

    def is_count_unreliable(self) -> bool:
        """Return true if device is jammed and cannot count."""
        raise NotImplementedError()

    async def count_balls(self) -> int:
        """Return the current ball count."""
        # wait until count is stable
        await self._count_stable.wait()
        assert self._last_count is not None
        return self._last_count

    def wait_for_count_stable(self):
        """Wait for stable count."""
        return asyncio.ensure_future(self._count_stable.wait())

    @property
    def is_ready_to_receive(self):
        """Return true if the counter is ready to receive."""
        raise NotImplementedError()

    async def wait_for_ready_to_receive(self):
        """Wait until the counter is ready to count an incoming ball."""
        raise NotImplementedError()

    async def wait_for_ball_to_leave(self):
        """Wait until a ball left."""
        raise NotImplementedError()

    def received_entrance_event(self):
        """Handle entrance event."""
        raise NotImplementedError()

    def register_change_stream(self):
        """Register queue which returns all changes."""
        queue = asyncio.Queue()
        self._activity_queues.append(queue)
        return queue

    def record_activity(self, activity_type: BallActivity) -> None:
        """Record an activity."""
        for queue in self._activity_queues:
            queue.put_nowait(activity_type)

    def wait_for_ball_activity(self):
        """Wait for (settled) ball activity in device."""
        future = asyncio.Future()
        self._ball_change_futures.append(future)
        return future

    @property
    def capacity(self):
        """Return capacity under normal circumstances.

        This should not include jam switches or similar overflow mechanisms.
        """
        raise NotImplementedError()

    # pylint: disable-msg=inconsistent-return-statements
    async def wait_for_ball_count_changes(self, old_count: int):
        """Wait for ball count changes and return the new count.

        Args:
        ----
            old_count: Old ball count. Will return when the current count differs
        """
        while True:
            current_count = await self.count_balls()
            if current_count != old_count:
                return current_count

            await self.wait_for_ball_activity()
