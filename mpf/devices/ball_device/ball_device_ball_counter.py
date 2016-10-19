"""Baseclass for ball device ball counters.

The duty of this device is to maintain the current ball count of the device.
"""
import asyncio


class BallDeviceBallCounter:

    """Ball counter for ball device."""

    def __init__(self, ball_device):
        """Initialise ball counter."""
        self.ball_device = ball_device

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
