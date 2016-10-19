"""Switch ball counter."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_ball_counter import BallDeviceBallCounter


class SwitchCounter(BallDeviceBallCounter):

    """Determine ball count by counting switches."""

    def __init__(self, ball_device):
        """Initialise ball counter."""
        super().__init__(ball_device)
        self._switch_change_condition = asyncio.Event(loop=self.ball_device.machine.clock.loop)
        
        # Register switch handlers with delays for entrance & exit counts
        for switch in self.ball_device.config['ball_switches']:
            self.ball_device.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=self.ball_device.config['entrance_count_delay'],
                callback=self._switch_changed)
        for switch in self.ball_device.config['ball_switches']:
            self.ball_device.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                ms=self.ball_device.config['exit_count_delay'],
                callback=self._switch_changed)

    def _switch_changed(self, **kwargs):
        del kwargs
        self._switch_change_condition.set()

    @asyncio.coroutine
    def count_balls(self):
        """Return the current ball count."""
        while True:
            self.ball_device.debug_log("Counting balls by checking switches")
            # register the waiter before counting to prevent races
            waiter = self.wait_for_ball_count_changes()
            try:
                balls = self._count_ball_switches()
                return balls
            except ValueError:
                yield from waiter

    def _count_ball_switches(self):
        """Count currently active switches or raise ValueError if switches are unstable."""
        ball_count = 0

        for switch in self.ball_device.config['ball_switches']:
            valid = False
            if self.ball_device.machine.switch_controller.is_active(
                    switch.name, ms=self.ball_device.config['entrance_count_delay']):
                ball_count += 1
                valid = True
                self.ball_device.debug_log("Confirmed active switch: %s", switch.name)
            elif self.ball_device.machine.switch_controller.is_inactive(
                    switch.name, ms=self.ball_device.config['exit_count_delay']):
                self.ball_device.debug_log("Confirmed inactive switch: %s", switch.name)
                valid = True

            if not valid:
                # one of our switches wasn't valid long enough
                self.ball_device.debug_log("Switch '%s' changed too recently. Aborting count!", switch.name)
                raise ValueError('Count not stable yet. Run again!')

        self.ball_device.debug_log("Counted %s balls", ball_count)
        return ball_count

    @asyncio.coroutine
    def wait_for_ball_count_changes(self):
        """Wait for ball count changes."""
        # TODO: only return when ball_count actually changed
        self._switch_change_condition.clear()
        yield from self._switch_change_condition.wait()

    def wait_for_ball_to_leave(self):
        """Wait for any active switch to become inactive."""
        waiters = []
        for switch in self.ball_device.config['ball_switches']:
            # only consider active switches
            if self.ball_device.machine.switch_controller.is_active(switch.name):
                waiters.append(self.ball_device.machine.switch_controller.wait_for_switch(
                    switch_name=switch.name,
                    state=0))

        if not waiters:
            # TODO: find out why this happens
            raise AssertionError("No switch is active. Cannot wait on empty list.")

        return Util.first(waiters, self.ball_device.machine.clock.loop)
