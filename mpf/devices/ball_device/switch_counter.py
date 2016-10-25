"""Switch ball counter."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_ball_counter import BallDeviceBallCounter


class SwitchCounter(BallDeviceBallCounter):

    """Determine ball count by counting switches.

    This should be used for devices with multiple switches and/or a jam switch. Simple devices with only one switch
    should use a simpler counter.
    """
    # TODO: write simpler counter

    def __init__(self, ball_device, config):
        """Initialise ball counter."""
        super().__init__(ball_device, config)
        # TODO: use ball_switches and jam_switch!
        # Register switch handlers with delays for entrance & exit counts
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=self.config['entrance_count_delay'],
                callback=self._switch_changed)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                ms=self.config['exit_count_delay'],
                callback=self._switch_changed)

        self._futures = []

    def _switch_changed(self, **kwargs):
        del kwargs
        for future in self._futures:
            if not future.done():
                future.set_result(True)
        self._futures = []

    @asyncio.coroutine
    def count_balls(self):
        """Return the current ball count."""
        while True:
            self.debug_log("Counting balls by checking switches")
            # register the waiter before counting to prevent races
            waiter = self.wait_for_ball_activity()
            try:
                balls = self.count_balls_sync()
                return balls
            except ValueError:
                yield from waiter

    def count_balls_sync(self):
        """Count currently active switches or raise ValueError if switches are unstable."""
        ball_count = 0

        for switch in self.config['ball_switches']:
            valid = False
            if self.machine.switch_controller.is_active(
                    switch.name, ms=self.config['entrance_count_delay']):
                ball_count += 1
                valid = True
                self.debug_log("Confirmed active switch: %s", switch.name)
            elif self.machine.switch_controller.is_inactive(
                    switch.name, ms=self.config['exit_count_delay']):
                self.debug_log("Confirmed inactive switch: %s", switch.name)
                valid = True

            if not valid:
                # one of our switches wasn't valid long enough
                self.debug_log("Switch '%s' changed too recently. Aborting count!", switch.name)
                raise ValueError('Count not stable yet. Run again!')

        self.debug_log("Counted %s balls", ball_count)
        return ball_count

    def wait_for_ball_activity(self):
        """Wait for ball count changes."""
        # TODO: only return when ball_count actually changed
        future = asyncio.Future(loop=self.machine.clock.loop)
        self._futures.append(future)
        return future

    def wait_for_ball_to_leave(self):
        """Wait for any active switch to become inactive."""
        waiters = []
        for switch in self.config['ball_switches']:
            # only consider active switches
            if self.machine.switch_controller.is_active(switch.name):
                waiters.append(self.machine.switch_controller.wait_for_switch(
                    switch_name=switch.name,    # TODO: readd ms here.
                    state=0))

        if not waiters:
            # TODO: raise exception and handle this in ball_device
            self.ball_device.log.warning("No switch is active. Cannot wait on empty list.")
            future = asyncio.Future(loop=self.machine.clock.loop)
            future.set_result(True)
            return future

        return Util.first(waiters, self.machine.clock.loop)
