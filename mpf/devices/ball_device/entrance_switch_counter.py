"""Count balls using an entrance switch."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_count_handler import EjectTracker
from mpf.devices.ball_device.ball_device_ball_counter import BallDeviceBallCounter


class EntranceSwitchCounter(BallDeviceBallCounter):

    """Count balls using an entrance switch."""

    def __init__(self, ball_device, config):
        """Initialise entrance switch counter."""
        super().__init__(ball_device, config)
        # Configure switch handlers for entrance switch activity
        self.machine.switch_controller.add_switch_handler(
            switch_name=self.config['entrance_switch'].name, state=1,
            ms=0,
            callback=self._entrance_switch_handler)

        if self.config['entrance_switch_full_timeout'] and self.config['ball_capacity']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['entrance_switch'].name, state=1,
                ms=self.config['entrance_switch_full_timeout'],
                callback=self._entrance_switch_full_handler)

        # Handle initial ball count with entrance_switch. If there is a ball on the entrance_switch at boot
        # assume that we are at max capacity.
        if (self.config['ball_capacity'] and self.config['entrance_switch_full_timeout'] and
                self.machine.switch_controller.is_active(self.config['entrance_switch'].name,
                                                         ms=self.config['entrance_switch_full_timeout'])):
            self._entrance_count = self.config['ball_capacity']
        else:
            self._entrance_count = 0

        self._futures = []

    def is_jammed(self) -> bool:
        """Return False because this device can not know if it is jammed."""
        return False

    def _set_future_results(self):
        for future in self._futures:
            if not future.done():
                future.set_result(True)
        self._futures = []

    def received_entrance_event(self):
        """Handle entrance event."""
        self._entrance_switch_handler()

    def _entrance_switch_handler(self):
        """Add a ball to the device since the entrance switch has been hit."""
        self._set_future_results()
        self.debug_log("Entrance switch hit")

        if self.config['ball_capacity'] and self.config['ball_capacity'] <= self._entrance_count:
            self.ball_device.log.warning("Device received balls but is already full!")

        # increase count
        self._entrance_count += 1

    def _entrance_switch_full_handler(self):
        # a ball is sitting on the entrance_switch. assume the device is full
        new_balls = self.config['ball_capacity'] - self._entrance_count
        if new_balls > 0:
            self._set_future_results()
            self.debug_log("Ball is sitting on entrance_switch. Assuming "
                           "device is full. Adding %s balls and setting balls"
                           "to %s", new_balls, self.config['ball_capacity'])
            self._entrance_count += new_balls

    def count_balls_sync(self):
        """Return the number of balls entered."""
        # TODO: ValueError when entrance switches are not stable
        return self._entrance_count

    @asyncio.coroutine
    def count_balls(self):
        """Return the number of balls entered."""
        # TODO: wait when entrance switch is not stable
        return self.count_balls_sync()

    def _wait_for_ball_to_leave(self):
        """Wait for a ball to leave."""
        if self.machine.switch_controller.is_active(self.config['entrance_switch'].name):
            return self.machine.switch_controller.wait_for_switch(
                switch_name=self.config['entrance_switch'].name,
                state=0)
        else:
            # wait 10ms
            done_future = asyncio.sleep(0.01, loop=self.machine.clock.loop)
            return Util.ensure_future(done_future, loop=self.machine.clock.loop)

    def wait_for_ball_activity(self):
        """Wait for ball count changes."""
        future = asyncio.Future(loop=self.machine.clock.loop)
        self._futures.append(future)
        return future

    @asyncio.coroutine
    def track_eject(self, eject_tracker: EjectTracker, already_left):
        """Remove one ball from count."""
        ball_left = self._wait_for_ball_to_leave() if not already_left else None
        ball_activity = self.wait_for_ball_activity()
        # we are stable from here on
        eject_tracker.set_ready()
        count = self._entrance_count
        while True:
            if ball_left:
                futures = [ball_activity, ball_left]
            else:
                futures = [ball_activity]

            yield from Util.any(futures, loop=self.machine.clock.loop)

            if ball_left and ball_left.done():
                ball_left = False
                eject_tracker.track_ball_left()
                self.debug_log("Device ejected a ball. Reducing ball count by one.")
                self._entrance_count -= 1
                count -= 1
                if self._entrance_count < 0:
                    self._entrance_count = 0
                    self.ball_device.log.warning("Entrance count went below 0")

            if ball_activity.done() and self._entrance_count > count:
                for _ in range(self._entrance_count - count):
                    yield from eject_tracker.track_ball_entrance()

                count = self._entrance_count
                ball_activity = self.wait_for_ball_activity()
