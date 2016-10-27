import asyncio

from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class IncomingBallsHandler(BallDeviceStateHandler):

    def __init__(self, ball_device):
        """Initialise incoming balls handler."""
        super().__init__(ball_device)
        # list of incoming balls sorted by their expiring time
        self._incoming_balls = asyncio.PriorityQueue(loop=self.machine.clock.loop)

        self.task = self.machine.clock.loop.create_task(self._run())

    @asyncio.coroutine
    def _run(self):
        pass

    # handle unexpected balls

    # handle incoming balls
