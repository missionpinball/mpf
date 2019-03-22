"""Maintains the ball count for a ball device."""
import asyncio

from typing import Generator

from mpf.devices.ball_device.physical_ball_counter import PhysicalBallCounter, EjectTracker
from mpf.devices.ball_device.entrance_switch_counter import EntranceSwitchCounter
from mpf.devices.ball_device.switch_counter import SwitchCounter

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class BallCountHandler(BallDeviceStateHandler):

    """Handles the ball count in the device."""

    __slots__ = ["_is_counting", "_count_valid", "_revalidate", "_eject_started", "_eject_ended", "_has_balls",
                 "_ball_count", "_ball_count_changed_futures", "counter"]

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
        self.counter = None  # type: PhysicalBallCounter

    def wait_for_ball_count_changed(self):
        """Wait until ball count changed."""
        future = asyncio.Future(loop=self.machine.clock.loop)
        self._ball_count_changed_futures.append(future)
        return future

    def stop(self):
        """Stop counter."""
        super().stop()
        if self.counter:
            self.counter.stop()
            self.counter = None

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

        self.machine.events.post("balldevice_{}_ball_count_changed".format(self.ball_device.name), balls=count)
        '''event: balldevice_(name)_ball_count_changed

        desc: The ball count for device (name) just changed.

        This event may also be called without a change in some circumstances.

        args:

        balls: The number of new balls in this device.
        '''

        for future in self._ball_count_changed_futures:
            if not future.done():
                future.set_result(count)

        # reset futures
        self._ball_count_changed_futures = []

    @asyncio.coroutine
    def initialise(self):
        """Initialise handler."""
        if self.ball_device.config['ball_switches']:
            self.counter = SwitchCounter(self.ball_device, self.ball_device.config)
        else:
            self.counter = EntranceSwitchCounter(self.ball_device, self.ball_device.config)

        self._ball_count = yield from self.counter.count_balls()
        # on start try to reorder balls if count is unstable
        if self.counter.is_count_unreliable():
            self.debug_log("BCH: Count is unstable. Trying to reorder balls.")
            yield from self.ball_device.ejector.reorder_balls()
            # recount
            self._ball_count = yield from self.counter.count_balls()

        if self._ball_count > 0:
            self._has_balls.set()
        self.ball_device.counted_balls = self._ball_count
        yield from super().initialise()
        self._count_valid.set()

    @property
    def has_ball(self) -> bool:
        """Return true if the device has at least one ball."""
        return self._ball_count > 0

    @property
    def is_full(self) -> bool:
        """Return true if the device is full."""
        return self.ball_device.config['ball_capacity'] - self._ball_count <= 0

    @asyncio.coroutine
    def wait_for_ball(self):
        """Wait until the device has a ball."""
        if self.has_ball:
            self.debug_log("We have %s balls.", self._ball_count)
            return

        self.debug_log("No ball found. Waiting for balls.")

        # wait until we have more than 0 balls
        ball_changes = Util.ensure_future(self.counter.wait_for_ball_count_changes(0),
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
    # pylint: disable-msg=inconsistent-return-statements
    def wait_for_ready_to_receive(self, source):
        """Wait until this device is ready to receive a ball."""
        while True:
            free_space = self.ball_device.config['ball_capacity'] - self._ball_count
            incoming_balls = self.ball_device.incoming_balls_handler.get_num_incoming_balls()
            if free_space <= incoming_balls:
                self.debug_log(
                    "Not ready to receive from %s. Not enough space. "
                    "Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                    source, free_space, self.ball_device.config['ball_capacity'], self._ball_count,
                    incoming_balls)
                yield from self.wait_for_ball_count_changed()
                continue

            if not self.counter.is_ready_to_receive:
                self.debug_log(
                    "Not ready to receive from %s. Waiting on counter to become ready. "
                    "Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                    source, free_space, self.ball_device.config['ball_capacity'], self._ball_count,
                    incoming_balls)
                # wait for the counter to be ready
                yield from self.counter.wait_for_ready_to_receive()
                continue

            # wait until any eject conditions have passed which would break on an incoming ball
            if not self.ball_device.outgoing_balls_handler.is_ready_to_receive:
                self.debug_log(
                    "Not ready to receive from %s. Target is currently ejecting. "
                    "Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                    source, free_space, self.ball_device.config['ball_capacity'], self._ball_count,
                    incoming_balls)
                yield from self.ball_device.outgoing_balls_handler.wait_for_ready_to_receive()
                continue

            self.debug_log("Ready to receive from %s. Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                           source, free_space, self.ball_device.config['ball_capacity'], self._ball_count,
                           incoming_balls)
            return True

    @asyncio.coroutine
    def start_eject(self, already_left=False) -> Generator[int, None, EjectTracker]:
        """Start eject."""
        yield from self.ball_device.incoming_balls_handler.start_eject()
        yield from self._is_counting.acquire()
        self._eject_started.set()
        self.debug_log("Entered eject mode.")

        eject_process = EjectTracker(self, already_left)
        if already_left:
            self._set_ball_count(self._ball_count + 1)
            yield from eject_process.will_eject()
        return eject_process

    @asyncio.coroutine
    def end_eject(self, eject_process: EjectTracker, ball_left):
        """End eject."""
        eject_process.cancel()
        self.debug_log("Exited eject mode. Eject success: %s", ball_left)
        if ball_left:
            self._set_ball_count(self._ball_count - 1)
        self._eject_started.clear()
        self._is_counting.release()
        self.ball_device.incoming_balls_handler.end_eject()

    @asyncio.coroutine
    def _run(self):
        changes = self.counter.register_change_stream()
        while True:
            # wait for ball changes
            ball_changes = Util.ensure_future(changes.get(), loop=self.machine.clock.loop)
            revalidate_future = Util.ensure_future(self._revalidate.wait(), loop=self.machine.clock.loop)
            yield from Util.first([ball_changes, revalidate_future, self._eject_started.wait()],
                                  loop=self.machine.clock.loop)
            self._revalidate.clear()

            # get lock and update count
            yield from self._is_counting.acquire()

            new_balls = yield from self.counter.count_balls()

            # try to re-order the device if count is unstable
            if self.counter.is_count_unreliable():
                self.debug_log("BCH: Count is unstable. Trying to reorder balls.")
                yield from self.ball_device.ejector.reorder_balls()
                new_balls = yield from self.counter.count_balls()

            self.debug_log("BCH: Counting. New count: %s Old count: %s", new_balls, self._ball_count)

            # when jammed do not trust other switches except the jam. keep old count
            if not self.counter.is_count_unreliable():
                # otherwise handle balls
                old_ball_count = self._ball_count
                if new_balls > old_ball_count:
                    self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
                    self._set_ball_count(new_balls)
                    # handle new balls via incoming balls handler
                    for _ in range(new_balls - old_ball_count):
                        yield from self.ball_device.incoming_balls_handler.ball_arrived()
                elif new_balls < old_ball_count:
                    yield from self._handle_missing_balls(new_balls, old_ball_count - new_balls)

            self._is_counting.release()
            self._count_valid.set()

    @asyncio.coroutine
    def _handle_missing_balls(self, new_balls, missing_balls):
        if self.ball_device.outgoing_balls_handler.is_idle:
            if self.ball_device.config['mechanical_eject']:
                self.debug_log("BCH: Lost %s balls. Assuming mechanical eject.", missing_balls)
                self._set_ball_count(new_balls)
                yield from self.ball_device.handle_mechanial_eject_during_idle()
            else:
                try:
                    yield from asyncio.wait_for(self.counter.wait_for_ball_activity(),
                                                loop=self.machine.clock.loop,
                                                timeout=self.ball_device.config['idle_missing_ball_timeout'])
                except asyncio.TimeoutError:
                    self.debug_log("BCH: Lost %s balls", missing_balls)
                    self._set_ball_count(new_balls)
                    for _ in range(missing_balls):
                        yield from self.ball_device.lost_idle_ball()
                else:
                    self._revalidate.set()
        else:
            self.debug_log("Lost ball %s balls between ejects. Ignoring.", missing_balls)

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
