"""Handles incoming balls."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class IncomingBall:

    """One incoming ball."""

    def __init__(self, source, target):
        """Initialise incoming ball."""
        self._timeout_future = asyncio.Future(loop=source.machine.clock.loop)
        self._confirm_future = asyncio.Future(loop=source.machine.clock.loop)
        self._source = source
        self._target = target
        self._left_device = True
        self._external_confirm_future = None

    @property
    def can_arrive(self):
        """Return true if ball can arrive."""
        return self._left_device and (not self._external_confirm_future or self._external_confirm_future.done())

    def add_external_confirm_switch(self, switch_name):
        """Add external confirm switch."""
        if self._external_confirm_future:
            raise AssertionError("Can only add external confirm once.")

        self._external_confirm_future = self._source.machine.switch_controller.wait_for_switch(switch_name)
        self._external_confirm_future.add_done_callback(self._external_confirm)

    def add_external_confirm_event(self, event):
        """Add external confirm event."""
        if self._external_confirm_future:
            raise AssertionError("Can only add external confirm once.")

        self._external_confirm_future = self._source.machine.events.wait_for_event(event)
        self._external_confirm_future.add_done_callback(self._external_confirm)

    def _external_confirm(self, future):
        del future
        self._timeout_future.cancel()
        timeout = self._source.config['ball_missing_timeouts'][self._target] / 1000
        self._timeout_future = self._source.ensure_future(asyncio.sleep(timeout, loop=self._source.machine.clock.loop))
        self._confirm_future.set_result(True)

    @property
    def source(self):
        """Return source."""
        return self._source

    @property
    def target(self):
        """Return target."""
        return self._target

    def did_not_arrive(self):
        """Ball did not arrive."""
        # self._confirm_future.cancel()
        self._timeout_future.cancel()
        self._target.remove_incoming_ball(self)

    def ball_arrived(self):
        """Ball did arrive."""
        if not self._external_confirm_future:
            self._confirm_future.set_result(True)
        self._timeout_future.cancel()

    def wait_for_confirm(self):
        """Wait for confirm."""
        return asyncio.shield(self._confirm_future, loop=self._source.machine.clock.loop)

    # TODO: states:
    # 1. ejecting (for space calculation
    # 2. left (can be confirmed)
    # 3. arrived
    # 4. timeouted


class IncomingBallsHandler(BallDeviceStateHandler):

    """Handles incoming balls and timeouts."""

    def __init__(self, ball_device):
        """Initialise incoming balls handler."""
        super().__init__(ball_device)
        # list of incoming balls sorted by their expiring time
        self._incoming_balls = []
        self._has_incoming_balls = asyncio.Event(loop=self.machine.clock.loop)

    @asyncio.coroutine
    def _run(self):
        """Handle timeouts."""
        while True:
            # sleep until we have incoming balls
            yield from self._has_incoming_balls.wait()

            futures = [incoming_ball._timeout_future for incoming_ball in self._incoming_balls]
            yield from Util.first(futures, cancel_others=False, loop=self.machine.clock.loop)

            timeouts = []
            for incoming_ball in self._incoming_balls:
                if incoming_ball._timeout_future.done() and not incoming_ball._timeout_future.cancelled():
                    timeouts.append(incoming_ball)

            for incoming_ball in timeouts:
                self.debug_log("Incoming ball timeout")
                self._incoming_balls.remove(incoming_ball)

            if not self._incoming_balls:
                self._has_incoming_balls.clear()

            for incoming_ball in timeouts:
                yield from self.ball_device.lost_incoming_ball(source=incoming_ball.source)

    def add_incoming_ball(self, incoming_ball: IncomingBall):
        """Add incoming balls."""
        self.debug_log("Adding incoming ball from %s", incoming_ball.source)
        self._incoming_balls.append(incoming_ball)
        # TODO: set a callback here
        self._has_incoming_balls.set()

    def remove_incoming_ball(self, incoming_ball: IncomingBall):
        """Remove incoming ball."""
        self.debug_log("Removing incoming ball from %s", incoming_ball.source)
        self._incoming_balls.remove(incoming_ball)

    @asyncio.coroutine
    def ball_arrived(self):
        """Handle one ball which arrived in the device."""
        for incoming_ball in self._incoming_balls:
            if not incoming_ball.can_arrive:
                continue

            # handle incoming ball
            self.debug_log("Received ball from %s", incoming_ball.source)
            # confirm eject
            incoming_ball.ball_arrived()
            self._incoming_balls.remove(incoming_ball)

            # TODO: post enter event here?
            yield from self.ball_device.expected_ball_received()
            break
        else:
            # handle unexpected ball
            self.debug_log("Received unexpected ball")
            # let the ball device handle this ball
            yield from self.ball_device.unexpected_ball_received()
