"""Maintains the ball count for a ball device."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class EjectTracker:

    """Tracks ball changes during an eject."""

    def __init__(self, ball_counter_handler, already_left):
        """Initialise eject tracker."""
        self.machine = ball_counter_handler.machine
        self._already_left = already_left
        self._ball_count_handler = ball_counter_handler
        self._task = None
        self._event_queue = asyncio.Queue(loop=self._ball_count_handler.machine.clock.loop)
        self._ball_left = asyncio.Future(loop=self._ball_count_handler.machine.clock.loop)
        self._ball_returned = asyncio.Future(loop=self._ball_count_handler.machine.clock.loop)
        self._ready = asyncio.Future(loop=self._ball_count_handler.machine.clock.loop)
        self._unknown_balls = asyncio.Future(loop=self._ball_count_handler.machine.clock.loop)
        self._num_unknown_balls = 0
        self._num_lost_balls = 0

    @asyncio.coroutine
    def will_eject(self):
        """Start process."""
        self._task = self.machine.clock.loop.create_task(
            self._ball_count_handler.ball_device.counter.track_eject(self, self._already_left))
        self._task.add_done_callback(self._done)
        yield from self.wait_for_ready()

    def cancel(self):
        """Cancel eject tracker."""
        if self._task:
            self._task.cancel()

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def is_jammed(self):
        """Return true if currently jammed."""
        return self._ball_count_handler.ball_device.counter.is_jammed()

    def track_ball_left(self):
        """Track ball left."""
        self._ball_count_handler.ball_device.debug_log("Got ball left during eject")
        self._ball_left.set_result(True)

    def track_ball_returned(self):
        """Track ball returned."""
        self._ball_count_handler.ball_device.debug_log("Got ball return during eject")
        self._ball_returned.set_result(True)

    @asyncio.coroutine
    def track_ball_entrance(self):
        """Track ball entrance."""
        self._ball_count_handler.ball_device.debug_log("Got ball entrance during eject")
        yield from self._ball_count_handler.entrance_during_eject()

    def track_unknown_balls(self, balls):
        """Track unknown ball."""
        self._ball_count_handler.ball_device.debug_log("Got %s unknown ball during eject", balls)
        self._num_unknown_balls += balls
        if not self._unknown_balls.done():
            self._unknown_balls.set_result(True)

    def track_lost_balls(self, balls):
        """Track lost ball."""
        self._num_lost_balls += balls
        if self._num_lost_balls >= self._num_unknown_balls and self._unknown_balls.done():
            self._unknown_balls = asyncio.Future(loop=self._ball_count_handler.machine.clock.loop)

    def wait_for_ball_return(self):
        """Wait until a ball returned."""
        return asyncio.shield(self._ball_returned, loop=self.machine.clock.loop)

    def wait_for_ball_unknown_ball(self):
        """Return true if the device has unknown balls which are neither clearly new or returned."""
        return asyncio.shield(self._unknown_balls, loop=self.machine.clock.loop)

    def wait_for_ball_left(self):
        """Wait until a ball left."""
        return asyncio.shield(self._ball_left, loop=self.machine.clock.loop)

    def wait_for_ready(self):
        """Wait until the device is ready."""
        return asyncio.shield(self._ready, loop=self.machine.clock.loop)

    def set_ready(self):
        """Set device ready."""
        self._ready.set_result("ready")

    def eject_success(self):
        """Mark eject successful."""
        self._task.cancel()
        self._ball_count_handler.eject_success()

    def ball_lost(self):
        """Mark eject failed and ball lost."""
        self._task.cancel()
        self._ball_count_handler.ball_lost()

    def ball_returned(self):
        """Mark eject failed and ball returned."""
        self._task.cancel()
        self._ball_count_handler.ball_returned()


class BallCountHandler(BallDeviceStateHandler):

    """Handles the ball count in the device."""

    def __init__(self, ball_device):
        """Initialise ball count handler."""
        super().__init__(ball_device)
        # inputs
        self._is_counting = asyncio.Lock(loop=self.machine.clock.loop)
        self._count_valid = asyncio.Event(loop=self.machine.clock.loop)
        self._revalidate = asyncio.Event(loop=self.machine.clock.loop)
        self._eject_started = asyncio.Event(loop=self.machine.clock.loop)
        self._eject_ended = asyncio.Event(loop=self.machine.clock.loop)
        self._has_balls = asyncio.Event(loop=self.machine.clock.loop)
        self._ball_count = 0
        self._ball_count_changed_futures = []

    def wait_for_ball_count_changed(self):
        """Wait until ball count changed."""
        future = asyncio.Future(loop=self.machine.clock.loop)
        self._ball_count_changed_futures.append(future)
        return future

    @property
    def handled_balls(self):
        """Return balls which are already handled."""
        return self._ball_count

    def _set_ball_count(self, count):
        self._ball_count = count
        # mirror variable at ball device for monitor
        self.ball_device.counted_balls = count
        if self._ball_count > 0:
            self._has_balls.set()
        else:
            self._has_balls.clear()

        for future in self._ball_count_changed_futures:
            if not future.done():
                future.set_result(count)

        # reset futures
        self._ball_count_changed_futures = []

    @asyncio.coroutine
    def initialise(self):
        """Initialise handler."""
        self._ball_count = yield from self.ball_device.counter.count_balls()
        if self._ball_count > 0:
            self._has_balls.set()
        self.ball_device.counted_balls = self._ball_count
        yield from super().initialise()
        self._count_valid.set()

    @property
    def has_ball(self):
        """Return true if the device has at least one ball."""
        return self._ball_count > 0

    @asyncio.coroutine
    def wait_for_ball(self):
        """Wait until the device has a ball."""
        if self.has_ball:
            self.debug_log("We have %s balls.", self._ball_count)
            return

        self.debug_log("No ball found. Waiting for balls.")

        # wait until we have more than 0 balls
        ball_changes = Util.ensure_future(self.ball_device.counter.wait_for_ball_count_changes(0),
                                          loop=self.machine.clock.loop)
        new_balls = yield from ball_changes

        # update count
        old_ball_count = self._ball_count
        self._ball_count = new_balls
        if new_balls > old_ball_count:
            self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
            # handle new balls via incoming balls handler
            for _ in range(new_balls - old_ball_count):
                yield from self.ball_device.incoming_balls_handler.ball_arrived()
            self._set_ball_count(new_balls)

        self.debug_log("A ball arrived. Progressing.")

    @asyncio.coroutine
    def wait_for_ready_to_receive(self, source):
        """Wait until this device is ready to receive a ball."""
        while True:
            free_space = self.ball_device.config['ball_capacity'] - self._ball_count
            incoming_balls = self.ball_device.incoming_balls_handler.get_num_incoming_balls()
            if free_space > incoming_balls:
                self.debug_log("Ready to receive from %s. Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                               source, free_space, self.ball_device.config['ball_capacity'], self._ball_count,
                               incoming_balls)
                # wait for the counter to be ready
                yield from self.ball_device.counter.wait_for_ready_to_receive()
                return True

            self.debug_log("Not ready to receive from %s. Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                           source, free_space, self.ball_device.config['ball_capacity'], self._ball_count,
                           incoming_balls)

            yield from self.wait_for_ball_count_changed()

    @asyncio.coroutine
    def start_eject(self):
        """Start eject."""
        yield from self._is_counting.acquire()
        self._eject_started.set()
        self.debug_log("Entered eject mode.")

    @asyncio.coroutine
    def end_eject(self):
        """End eject."""
        self.debug_log("Exited eject mode.")
        self._eject_started.clear()
        self._is_counting.release()

    @asyncio.coroutine
    def track_eject(self, already_left=False) -> EjectTracker:
        """Start an eject."""
        eject_process = EjectTracker(self, already_left)
        if already_left:
            self._set_ball_count(self._ball_count + 1)
            yield from eject_process.will_eject()
        return eject_process

    @asyncio.coroutine
    def _run(self):
        while True:
            # wait for ball changes
            ball_changes = Util.ensure_future(self.ball_device.counter.wait_for_ball_activity(),
                                              loop=self.machine.clock.loop)
            revalidate_future = Util.ensure_future(self._revalidate.wait(), loop=self.machine.clock.loop)
            event = yield from Util.first([ball_changes, revalidate_future, self._eject_started.wait()],
                                          loop=self.machine.clock.loop)
            self._revalidate.clear()

            # get lock and update count
            if self._is_counting.locked():
                self.debug_log("Waiting for eject to end")
                yield from self._is_counting.acquire()
                new_balls = yield from self.ball_device.counter.count_balls()
                self.debug_log("Eject ended")
            elif event == revalidate_future:
                yield from self._is_counting.acquire()
                new_balls = yield from self.ball_device.counter.count_balls()
            else:
                if event != ball_changes:
                    raise AssertionError("Event order problem")
                yield from self._is_counting.acquire()
                new_balls = yield from self.ball_device.counter.count_balls()

            self.debug_log("Counting idle")

            # when jammed do not trust other switches except the jam. keep old count
            if not self.ball_device.counter.is_jammed() or new_balls != 1:
                # otherwise handle balls
                old_ball_count = self._ball_count
                self._set_ball_count(new_balls)
                if new_balls > old_ball_count:
                    self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
                    # handle new balls via incoming balls handler
                    for _ in range(new_balls - old_ball_count):
                        yield from self.ball_device.incoming_balls_handler.ball_arrived()
                elif new_balls < old_ball_count:
                    self.debug_log("BCH: Lost %s balls", old_ball_count - new_balls)
                    for _ in range(old_ball_count - new_balls):
                        yield from self.ball_device.lost_idle_ball()

            self._is_counting.release()
            self._count_valid.set()

    @asyncio.coroutine
    def wait_for_count_is_valid(self):
        """Wait until count is valid."""
        self._count_valid.clear()
        self._revalidate.set()
        # wait for ball_counter to become ready
        yield from self._count_valid.wait()

    @asyncio.coroutine
    def entrance_during_eject(self):
        """Received an entrance during eject."""
        yield from self.ball_device.incoming_balls_handler.ball_arrived()
        self._set_ball_count(self._ball_count + 1)

    def eject_success(self):
        """Eject successful."""
        self.debug_log("Received eject success.")
        self._set_ball_count(self._ball_count - 1)

    def ball_lost(self):
        """Eject failed. Lost ball."""
        self.ball_device.log.warning("Received eject failed. Eject lost ball.")
        self._set_ball_count(self._ball_count - 1)

    def ball_returned(self):
        """Eject failed. Ball returned."""
        self.debug_log("Received eject failed. Ball returned.")
