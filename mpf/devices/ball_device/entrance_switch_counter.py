import asyncio

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

        self._ball_entered_condition = asyncio.Event(loop=self.ball_device.machine.clock.loop)

    def _entrance_switch_handler(self):
        """Add a ball to the device since the entrance switch has been hit."""
        # TODO: maintain recycle_time somewhere
        self._ball_entered_condition.set()
        self.debug_log("Entrance switch hit")

        if self.config['ball_capacity'] and self.config['ball_capacity'] == self._entrance_count:
            self.ball_device.log.warning("Device received balls but is already full. Ignoring!")
            # TODO: ball should be added to pf instead
            return

        # increase count
        self._entrance_count += 1

    def _entrance_switch_full_handler(self):
        # a ball is sitting on the entrance_switch. assume the device is full
        new_balls = self.config['ball_capacity'] - self._entrance_count
        if new_balls > 0:
            self._ball_entered_condition.set()
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

    def wait_for_ball_to_leave(self):
        """Wait for a ball to leave."""
        if self.machine.switch_controller.is_active(self.config['entrance_switch'].name):
            return self.machine.switch_controller.wait_for_switch(
                switch_name=self.config['entrance_switch'].name,
                state=0)
        else:
            # TODO: put some minimal wait here
            done_future = asyncio.Future(loop=self.machine.clock.loop)
            done_future.set_result(True)
            return done_future

    def wait_for_ball_count_changes(self):
        """Wait for ball count changes."""
        # TODO: convert to individual futures
        self._ball_entered_condition.clear()
        return self._ball_entered_condition.wait()

    def ejecting_one_ball(self):
        """Remove one ball from count."""
        self._entrance_count -= 1
        self.debug_log("Device ejected a ball. Reducing ball count by one.")
        if self._entrance_count < 0:
            self._entrance_count = 0
            self.ball_device.log.warning("Ball count went negative. Resetting!")
