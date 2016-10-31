import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class EjectProcessCounter:

    def __init__(self, ball_counter_handler):
        self._ball_count_handler = ball_counter_handler
        self._hardware_counter_state = None
        self._eject_done = asyncio.Future(loop=self._ball_count_handler.machine.clock.loop)

    def start(self):
        """Start processs."""
        self._hardware_counter_state = self._ball_count_handler.ball_device.counter.ejecting_one_ball()

    def is_jammed(self):
        """Return true if currently jammed."""
        return self._ball_count_handler.ball_device.counter.is_jammed()

    def wait_for_ball_return(self):
        return self._ball_count_handler.ball_device.counter.wait_for_ball_to_return(self._hardware_counter_state)

    def wait_for_ball_left(self):
        return self._ball_count_handler.ball_device.counter.wait_for_ball_to_leave(self._hardware_counter_state)

    def wait_for_ball_entrance(self):
        return self._ball_count_handler.ball_device.counter.wait_for_ball_entrance(self._hardware_counter_state)

    def wait_for_eject_done(self):
        return self._eject_done

    def eject_done(self):
        self._eject_done.set_result(True)

    def eject_failed(self):
        self._eject_done.set_result(False)


class BallCountHandler(BallDeviceStateHandler):

    """Handles the ball count in the device."""

    def __init__(self, ball_device):
        """Initialise ball count handler."""
        super().__init__(ball_device)
        # inputs
        self._ejects = asyncio.Queue(loop=self.machine.clock.loop)
        self._has_balls = asyncio.Event(loop=self.machine.clock.loop)
        self._ball_count = 0

    @property
    def handled_balls(self):
        """Return balls which are already handled."""
        return self._ball_count

    @asyncio.coroutine
    def initialise(self):
        """Initialise handler."""
        self._ball_count = yield from self.ball_device.counter.count_balls()
        if self._ball_count > 0:
            self._has_balls.set()
        yield from super().initialise()

    def wait_for_ball(self):
        """Wait until the device has a ball."""
        return self._has_balls.wait()

    def get_ball_count(self):
        """Return a ball count future."""
        return self.ball_device.counter.count_balls()   # TODO: internalise counter

    def start_eject(self) -> EjectProcessCounter:
        """Start an eject."""
        eject_process = EjectProcessCounter(self)
        eject_process.start()
        self._ejects.put_nowait(eject_process)
        return eject_process

    @asyncio.coroutine
    def _run(self):
        while True:
            # wait for ball changes
            ball_changes = self.ball_device.ensure_future(
                self.ball_device.counter.wait_for_ball_count_changes(self._ball_count))
            # wait for an eject to start
            eject_process = self.ball_device.ensure_future(self._ejects.get())

            event = yield from Util.first([ball_changes, eject_process], loop=self.machine.clock.loop)

            if eject_process.done():
                # this will be false before the entry in eject_done is added so this should not race
                eject_process = yield from eject_process
                yield from self._handle_entrance_during_eject(eject_process)
                self.debug_log("Counting in normal mode")
            elif event == ball_changes:
                # if old_ball_count != self.ball_device.balls:
                #     raise AssertionError("Ball count changed unexpectedly!")
                #     # TODO: internalise count and add getter in ball_device
                new_balls = yield from ball_changes
                old_ball_count = self._ball_count
                self._ball_count = new_balls
                if new_balls > old_ball_count:
                    self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
                    # handle new balls via incoming balls handler
                    for _ in range(new_balls - old_ball_count):
                        self.ball_device.incoming_balls_handler.ball_arrived()
                else:
                    self.debug_log("BCH: Lost %s balls", old_ball_count - new_balls)
                    # TODO: handle lost balls via outgoing balls handler (if mechanical eject)
                    # TODO: handle lost balls via lost balls handler (if really lost)
                    pass

                if self._ball_count > 0:
                    self._has_balls.set()
                else:
                    self._has_balls.clear()

    @asyncio.coroutine
    def _handle_entrance_during_eject(self, eject_process: EjectProcessCounter):
        """Wait until the eject is done and handle limited ball entrance."""
        self.debug_log("Counting in eject mode")
        # if we are 100% certain that this ball entered and did not return
        ball_entrance = self.ball_device.ensure_future(eject_process.wait_for_ball_entrance())
        ball_left = self.ball_device.ensure_future(eject_process.wait_for_ball_left())
        eject_done = self.ball_device.ensure_future(eject_process.wait_for_eject_done())
        futures = [ball_left, eject_done, ball_entrance]
        while True:
            event = yield from Util.first(futures, loop=self.machine.clock.loop, cancel_others=False)

            if event == ball_left:
                futures = [eject_done, ball_entrance]
                # remove one ball
                self._ball_count -= 1
            if eject_done.done():
                result = yield from eject_done
                self._handle_eject_done(result)
                return

            if ball_entrance.done():
                # TODO: handle new ball via incoming balls handler
                ball_entrance = self.ball_device.ensure_future(self.ball_device.counter.wait_for_ball_entrance())

    def _handle_eject_done(self, result):
        """Decrement count by one and handle failures."""
        if result:
            self.debug_log("Received eject done.")
        else:
            self.ball_device.log.warning("Received eject done but eject lost ball. Handling lost ball.")
            # TODO: handle lost balls via lost balls handler
            raise AssertionError("handle this")
