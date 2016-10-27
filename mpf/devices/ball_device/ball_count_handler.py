import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class BallCountHandler(BallDeviceStateHandler):

    """Handles the ball count in the device."""

    def __init__(self, ball_device):
        """Initialise ball count handler."""
        super().__init__(ball_device)
        # inputs
        self._currently_ejecting = asyncio.Event(loop=self.machine.clock.loop)   # TODO: use correct one
        self._eject_success = asyncio.Queue(loop=self.machine.clock.loop)   # TODO: use correct one

        self._task = None
        self._ball_count = 0

    @asyncio.coroutine
    def initialise(self):
        """Initialise handler."""
        self._ball_count = yield from self.ball_device.counter.count_balls()
        self._task = self.machine.clock.loop.create_task(self._handle_ball_count_changes())
        self._task.add_done_callback(self._done)

    def _done(self, future):
        future.result()

    @asyncio.coroutine
    def _handle_ball_count_changes(self):
        while True:
            # wait for ball changes
            ball_changes = self.ball_device.ensure_future(
                self.ball_device.counter.wait_for_ball_count_changes(self._ball_count))
            # wait for an eject to start
            eject_process = self.ball_device.ensure_future(self._currently_ejecting.wait())
            # in case we missed an eject
            eject_done = self.ball_device.ensure_future(self._eject_success.get())

            event = yield from Util.first([ball_changes, eject_process, eject_done], loop=self.machine.clock.loop)
            if eject_done.done():
                # we missed the eject and handle this out of order
                self.debug_log("Received eject done out of order.")
                result = yield from eject_done
                self._handle_eject_done(result)
            elif self._currently_ejecting.is_set():
                # this will be false before the entry in eject_done is added so this should not race
                yield from self._handle_entrance_during_eject()
            elif event == ball_changes:
                # if old_ball_count != self.ball_device.balls:
                #     raise AssertionError("Ball count changed unexpectedly!")
                #     # TODO: internalise count and add getter in ball_device
                new_balls = yield from ball_changes
                old_ball_count = self._ball_count
                self._ball_count = new_balls
                if new_balls > old_ball_count:
                    self.debug_log("BCH: Found %s new balls", new_balls - old_ball_count)
                    # TODO: handle new balls via incoming balls handler
                    pass
                else:
                    self.debug_log("BCH: Lost %s balls", old_ball_count - new_balls)
                    # TODO: handle lost balls via outgoing balls handler (if mechanical eject)
                    # TODO: handle lost balls via lost balls handler (if really lost)
                    pass

    @asyncio.coroutine
    def _handle_entrance_during_eject(self):
        """Wait until the eject is done and handle limited ball entrance."""
        # we will retirm when eject is done
        eject_done = self.ball_device.ensure_future(self._eject_success.get())
        # if we are 100% certain that this ball entered and did not return
        ball_entrance = self.ball_device.ensure_future(self.ball_device.counter.wait_for_ball_entrance())
        while True:
            event = yield from Util.first([eject_done, ball_entrance], loop=self.machine.clock.loop,
                                          cancel_others=False)

            if event == eject_done:
                result = yield from eject_done
                ball_entrance.cancel()
                self._handle_eject_done(result)
                return
            elif event == ball_entrance:
                # TODO: handle new ball via incoming balls handler
                ball_entrance = self.ball_device.ensure_future(self.ball_device.counter.wait_for_ball_entrance())

    def _handle_eject_done(self, result):
        """Decrement count by one and handle failures."""
        # remove one ball
        self._ball_count -= 1
        if result:
            self.debug_log("Received eject done.")
        else:
            self.ball_device.log.warning("Received eject done but eject lost ball. Handling lost ball.")
            # TODO: handle lost balls via lost balls handler
