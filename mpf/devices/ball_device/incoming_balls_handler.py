import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class IncomingBall:

    def __init__(self):
        self.timeout_future = None
        self.confirm_future = None
        self.source = None


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

            futures = [incoming_ball.timeout_future for incoming_ball in self._incoming_balls]
            yield from Util.first(futures, cancel_others=False, loop=self.machine.clock.loop)

            timeouts = []
            for incoming_ball in self._incoming_balls:
                if incoming_ball.timeout_future.done() and not incoming_ball.timeout_future.canceled():
                    timeouts.append(incoming_ball)

            for incoming_ball in timeouts:
                self.debug_log("Incoming ball timeout")
                self._incoming_balls.remove(incoming_ball)
                self._handle_timeout(incoming_ball)

            if not self._incoming_balls:
                self._has_incoming_balls.clear()

    def _handle_timeout(self, incoming_ball: IncomingBall):
        raise AssertionError("Ball Timeout")

    def add_incoming_ball(self, incoming_ball: IncomingBall):
        """Add incoming balls."""
        self._incoming_balls.append(incoming_ball)
        self._has_incoming_balls.set()

    def remove_incoming_ball(self, incoming_ball: IncomingBall):
        """Remove incoming ball."""
        self._incoming_balls.remove(incoming_ball)

    @asyncio.coroutine
    def ball_arrived(self):
        """Handle one ball which arrived in the device."""
        if self._incoming_balls:
            # handle incoming ball
            incoming_ball = self._incoming_balls.pop(0)     # TODO: sort by better metric
            self.debug_log("Received ball from %s", incoming_ball.source)
            incoming_ball.timeout_future.cancel()
            # confirm eject
            incoming_ball.confirm_future.set_result(True)

            # TODO: post enter event here?
            yield from self.ball_device.expected_ball_received()
        else:
            # handle unexpected ball
            self.debug_log("Received unexpected ball")
            # let the ball device handle this ball
            yield from self.ball_device.unexpected_ball_received()
