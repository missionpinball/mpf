"""Baseclass for ball device ball counters.

The duty of this device is to maintain the current ball count of the device.
"""
import asyncio


# TODO: rename to hardware counter
from typing import Generator

from mpf.devices.ball_device.ball_count_handler import EjectTracker


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

    def count_balls_sync(self) -> int:
        """Return the number of current active switches or raises ValueError when count is not stable."""
        raise NotImplementedError()

    def is_jammed(self) -> bool:
        """Return true if device is jammed."""
        raise NotImplementedError()

    @asyncio.coroutine
    def count_balls(self) -> Generator[int, None, int]:
        """Return the current ball count."""
        while True:
            # register the waiter before counting to prevent races
            waiter = self.wait_for_ball_activity()
            try:
                balls = self.count_balls_sync()
                waiter.cancel()
                return balls
            except ValueError:
                yield from waiter

    def wait_for_ball_activity(self):
        """Wait for ball activity."""
        raise NotImplementedError()

    def wait_for_ready_to_receive(self):
        """Wait until the counter is ready to count an incoming ball."""
        raise NotImplementedError()

    def received_entrance_event(self):
        """Handle entrance event."""
        pass

    @asyncio.coroutine
    def wait_for_ball_count_changes(self, old_count: int):
        """Wait for ball count changes and return the new count.

        Args:
            old_count: Old ball count. Will return when the current count differs
        """
        while True:
            current_count = yield from self.count_balls()
            if current_count != old_count:
                return current_count

            yield from self.wait_for_ball_activity()

    @asyncio.coroutine
    def track_eject(self, eject_tracker: EjectTracker, already_left):
        """Return eject_process dict."""
        raise NotImplementedError()
