"""Maintains the ball count for a ball device."""
import asyncio
from typing import Optional

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
        self._is_counting = asyncio.Lock()
        self._count_valid = asyncio.Event()
        self._revalidate = asyncio.Event()
        self._eject_started = asyncio.Event()
        self._eject_ended = asyncio.Event()
        self._has_balls = asyncio.Event()
        self._ball_count = 0
        self._ball_count_changed_futures = []
        self.counter = None  # type: Optional[PhysicalBallCounter]

    def wait_for_ball_count_changed(self):
        """Wait until ball count changed."""
        future = asyncio.Future()
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
        config_section: ball_devices
        class_label: ball_device

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

    async def initialise(self):
        """Initialise handler."""
        counter_config = self.ball_device.config.get("counter", {})
        if counter_config:
            counter_class = Util.string_to_class(counter_config["class"])
        elif self.ball_device.config.get('ball_switches'):
            counter_class = SwitchCounter
        else:
            counter_class = EntranceSwitchCounter

        self.counter = counter_class(self.ball_device, self.ball_device.config.get("counter", {}))

        self._ball_count = await self.counter.count_balls()
        # on start try to reorder balls if count is unstable
        if self.counter.is_count_unreliable():
            self.debug_log("BCH: Count is unstable. Trying to reorder balls.")
            await self.ball_device.ejector.reorder_balls()
            # recount
            self._ball_count = await self.counter.count_balls()

        if self._ball_count > 0:
            self._has_balls.set()
        self.ball_device.counted_balls = self._ball_count
        await super().initialise()
        self._count_valid.set()

    @property
    def has_ball(self) -> bool:
        """Return true if the device has at least one ball."""
        return self._ball_count > 0

    @property
    def is_full(self) -> bool:
        """Return true if the device is full."""
        if not self.counter:
            raise asyncio.CancelledError
        return self.counter.capacity - self._ball_count <= 0

    async def wait_for_ball(self):
        """Wait until the device has a ball."""
        if self.has_ball:
            self.debug_log("We have %s balls.", self._ball_count)
            return

        self.debug_log("No ball found. Waiting for balls.")

        # wait until we have more than 0 balls
        if not self.counter:
            raise asyncio.CancelledError
        ball_changes = asyncio.ensure_future(self.counter.wait_for_ball_count_changes(0))
        new_balls = await ball_changes

        # update count
        old_ball_count = self._ball_count
        self._ball_count = new_balls
        if new_balls > old_ball_count:
            self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
            # handle new balls via incoming balls handler
            for _ in range(new_balls - old_ball_count):
                await self.ball_device.incoming_balls_handler.ball_arrived()
            self._set_ball_count(new_balls)

        self.debug_log("A ball arrived. Progressing.")

    # pylint: disable-msg=inconsistent-return-statements
    async def wait_for_ready_to_receive(self, source):
        """Wait until this device is ready to receive a ball."""
        while True:
            if not self.counter:
                raise asyncio.CancelledError
            free_space = self.counter.capacity - self._ball_count
            incoming_balls = self.ball_device.incoming_balls_handler.get_num_incoming_balls()
            if free_space <= incoming_balls:
                self.debug_log(
                    "Not ready to receive from %s. Not enough space. "
                    "Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                    source, free_space, self.counter.capacity, self._ball_count,
                    incoming_balls)
                await self.wait_for_ball_count_changed()
                continue

            if not self.counter:
                raise asyncio.CancelledError
            if not self.counter.is_ready_to_receive:
                self.debug_log(
                    "Not ready to receive from %s. Waiting on counter to become ready. "
                    "Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                    source, free_space, self.counter.capacity, self._ball_count,
                    incoming_balls)
                # wait for the counter to be ready
                await self.counter.wait_for_ready_to_receive()
                continue

            # wait until any eject conditions have passed which would break on an incoming ball
            if not self.ball_device.outgoing_balls_handler.is_ready_to_receive:
                self.debug_log(
                    "Not ready to receive from %s. Target is currently ejecting. "
                    "Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                    source, free_space, self.counter.capacity, self._ball_count,
                    incoming_balls)
                await self.ball_device.outgoing_balls_handler.wait_for_ready_to_receive()
                continue

            if not self.counter:
                raise asyncio.CancelledError
            self.debug_log("Ready to receive from %s. Free space %s (Capacity: %s, Balls: %s), incoming_balls: %s",
                           source, free_space, self.counter.capacity, self._ball_count,
                           incoming_balls)
            return True

    async def start_eject(self, already_left=False) -> EjectTracker:
        """Start eject."""
        await self.ball_device.incoming_balls_handler.start_eject()
        await self._is_counting.acquire()
        self._eject_started.set()
        self.debug_log("Entered eject mode.")

        eject_process = EjectTracker(self, already_left)
        if already_left:
            self._set_ball_count(self._ball_count + 1)
            await eject_process.will_eject()
        return eject_process

    async def end_eject(self, eject_process: EjectTracker, ball_left):
        """End eject."""
        eject_process.cancel()
        self.debug_log("Exited eject mode. Eject success: %s", ball_left)
        if ball_left:
            self._set_ball_count(self._ball_count - 1)
        self._eject_started.clear()
        self._is_counting.release()
        self.ball_device.incoming_balls_handler.end_eject()

    async def _run(self):
        if not self.counter:
            raise asyncio.CancelledError
        changes = self.counter.register_change_stream()
        while True:
            # wait for ball changes
            ball_changes = asyncio.ensure_future(changes.get())
            revalidate_future = asyncio.ensure_future(self._revalidate.wait())
            await Util.first([ball_changes, revalidate_future, self._eject_started.wait()])
            self._revalidate.clear()

            # get lock and update count
            await self._is_counting.acquire()

            if not self.counter:
                raise asyncio.CancelledError
            new_balls = await self.counter.count_balls()

            # try to re-order the device if count is unstable
            if not self.counter:
                raise asyncio.CancelledError
            if self.counter.is_count_unreliable():
                self.debug_log("BCH: Count is unstable. Trying to reorder balls.")
                await self.ball_device.ejector.reorder_balls()
                new_balls = await self.counter.count_balls()

            self.debug_log("BCH: Counting. New count: %s Old count: %s", new_balls, self._ball_count)

            # when jammed do not trust other switches except the jam. keep old count
            if not self.counter:
                raise asyncio.CancelledError
            if not self.counter.is_count_unreliable():
                # otherwise handle balls
                old_ball_count = self._ball_count
                if new_balls > old_ball_count:
                    self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
                    self._set_ball_count(new_balls)
                    # handle new balls via incoming balls handler
                    for _ in range(new_balls - old_ball_count):
                        await self.ball_device.incoming_balls_handler.ball_arrived()
                elif new_balls < old_ball_count:
                    await self._handle_missing_balls(new_balls, old_ball_count - new_balls)

            self._is_counting.release()
            self._count_valid.set()

    async def _handle_missing_balls(self, new_balls, missing_balls):
        if self.ball_device.outgoing_balls_handler.is_idle:
            if self.ball_device.config['mechanical_eject']:
                self.debug_log("BCH: Lost %s balls. Assuming mechanical eject.", missing_balls)
                self._set_ball_count(new_balls)
                await self.ball_device.handle_mechanial_eject_during_idle()
            else:
                try:
                    if not self.counter:
                        raise asyncio.CancelledError
                    await asyncio.wait_for(self.counter.wait_for_ball_activity(),
                                           timeout=self.ball_device.config['idle_missing_ball_timeout'])
                except asyncio.TimeoutError:
                    self.debug_log("BCH: Lost %s balls", missing_balls)
                    self._set_ball_count(new_balls)
                    for _ in range(missing_balls):
                        await self.ball_device.lost_idle_ball()
                else:
                    self._revalidate.set()
        else:
            self.debug_log("Lost ball %s balls between ejects. Ignoring.", missing_balls)

    async def wait_for_count_is_valid(self):
        """Wait until count is valid."""
        self._count_valid.clear()
        self._revalidate.set()
        # wait for ball_counter to become ready
        await self._count_valid.wait()

    async def entrance_during_eject(self):
        """Received an entrance during eject."""
        await self.ball_device.incoming_balls_handler.ball_arrived()
        self._set_ball_count(self._ball_count + 1)
