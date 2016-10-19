import asyncio

from mpf.devices.ball_device.ball_device_ball_counter import BallDeviceBallCounter


class EntranceSwitchCounter(BallDeviceBallCounter):

    @asyncio.coroutine
    def count_balls(self):
        """Return the number of current active switches."""
        raise NotImplementedError()

    @asyncio.coroutine
    def wait_for_ball_to_leave(self):
        """Wait for a ball to leave."""
        raise NotImplementedError()

    @asyncio.coroutine
    def wait_for_ball_count_changes(self):
        """Wait for ball count changes."""
        raise NotImplementedError()

    @staticmethod
    def ejecting_one_ball():
        """Inform counter that one ball has been ejected."""
        pass