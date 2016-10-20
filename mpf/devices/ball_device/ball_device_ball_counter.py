"""Baseclass for ball device ball counters.

The duty of this device is to maintain the current ball count of the device.
"""
import asyncio


class BallDeviceBallCounter:

    """Ball counter for ball device."""

    def __init__(self, ball_device, config):
        """Initialise ball counter."""
        self.ball_device = ball_device
        self.config = config
        self.machine = self.ball_device.machine

    def debug_log(self, *args, **kwargs):
        """Debug log."""
        self.ball_device.debug_log(*args, **kwargs)

    @asyncio.coroutine
    def count_balls(self):
        """Return the number of current active switches."""
        raise NotImplementedError()

    def wait_for_ball_to_leave(self):
        """Wait for a ball to leave."""
        raise NotImplementedError()

    def wait_for_ball_count_changes(self):
        """Wait for ball count changes."""
        raise NotImplementedError()

    def ejecting_one_ball(self):
        """Inform counter that one ball has been ejected."""
        del self
