"""Switch ball counter."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.physical_ball_counter import PhysicalBallCounter, EjectTracker, BallLostActivity, \
    BallEntranceActivity, UnknownBallActivity, BallReturnActivity


class SwitchCounter(PhysicalBallCounter):

    """Determine ball count by counting switches.

    This should be used for devices with multiple switches and/or a jam switch. Simple devices with only one switch
    should use a simpler counter.
    """

    __slots__ = ["_entrances", "_trigger_recount", "_task", "_is_unreliable"]

    def __init__(self, ball_device, config):
        """Initialise ball counter."""
        super().__init__(ball_device, config)
        self._entrances = []
        self._trigger_recount = asyncio.Event(loop=self.machine.clock.loop)
        # Register switch handlers with delays for entrance & exit counts
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=self.config['entrance_count_delay'],
                callback=self.trigger_recount)
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                callback=self.invalidate_count)
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                ms=self.config['exit_count_delay'],
                callback=self.trigger_recount)
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                callback=self.invalidate_count)

        self._task = self.machine.clock.loop.create_task(self._run())
        self._is_unreliable = False

    def stop(self):
        """Stop task."""
        super().stop()
        if self._task:
            self._task.cancel()

    def trigger_recount(self):
        """Trigger a count."""
        self._trigger_recount.set()

    @asyncio.coroutine
    def _recount(self):
        while True:
            yield from self._trigger_recount.wait()
            self._trigger_recount.clear()
            try:
                balls = self.count_balls_sync()
                return balls
            except ValueError:
                continue

    @asyncio.coroutine
    def _run(self):
        self._trigger_recount.set()
        while True:
            new_count = yield from self._recount()
            self._count_stable.set()

            if self._last_count is None:
                self._last_count = new_count
            elif self._last_count < 0:
                raise AssertionError("Count may never be negativ")

            if self.is_jammed() and new_count == 1:
                # only jam is active. keep previous count
                self.debug_log("Counter is jammed. Only jam is active. Will no longer trust count.")
                # ball potentially returned
                if not self._is_unreliable:
                    self.trigger_activity()
                    self.record_activity(BallReturnActivity())
                    self._is_unreliable = True
                continue
            else:
                self._is_unreliable = False

            if new_count == self._last_count:
                # count did not change
                continue

            if new_count > self._last_count:
                # new ball
                for _ in range(new_count - self._last_count):
                    try:
                        last_entrance = self._entrances.pop(0)
                    except IndexError:
                        last_entrance = -1000

                    if last_entrance > self.machine.clock.get_time() - self.config['entrance_event_timeout']:
                        self.record_activity(BallEntranceActivity())
                    else:
                        self.record_activity(UnknownBallActivity())
            elif new_count < self._last_count:
                # lost ball
                for _ in range(self._last_count - new_count):
                    self.record_activity(BallLostActivity())

            # update count
            self._last_count = new_count
            self.trigger_activity()

    def received_entrance_event(self):
        """Handle entrance event."""
        entrance_time = self.machine.clock.get_time()
        entrance_timeout = self.config['entrance_event_timeout']
        self._entrances = [entrance for entrance in self._entrances if entrance > entrance_time - entrance_timeout]
        self._entrances.append(entrance_time)

    def _count_switches_sync(self):
        """Return active switches or raise ValueError if switches are unstable."""
        switches = []
        for switch in self.config['ball_switches']:
            valid = False
            if self.machine.switch_controller.is_active(
                    switch.name, ms=self.config['entrance_count_delay']):
                switches.append(switch.name)
                valid = True
            elif self.machine.switch_controller.is_inactive(
                    switch.name, ms=self.config['exit_count_delay']):
                valid = True

            if not valid:
                # one of our switches wasn't valid long enough
                self.debug_log("Switch '%s' changed too recently. Aborting count!", switch.name)
                raise ValueError('Count not stable yet. Run again!')

        return switches

    def count_balls_sync(self):
        """Count currently active switches or raise ValueError if switches are unstable."""
        switches = self._count_switches_sync()
        ball_count = len(switches)

        self.debug_log("Counted %s balls. Active switches: %s. Old: %s", ball_count, switches, self._last_count)
        return ball_count

    def is_jammed(self):
        """Return true if the jam switch is currently active."""
        return self.config['jam_switch'] and self.machine.switch_controller.is_active(
            self.config['jam_switch'].name, ms=self.config['entrance_count_delay'])

    def is_count_unreliable(self):
        """Return true if only the jam switch is active and the count is unknown."""
        return self._is_unreliable

    @property
    def is_ready_to_receive(self):
        """Return true if count is stable and we got at least one slot."""
        try:
            count = self._count_switches_sync()
        except ValueError:
            # count not stable
            return False
        return count != len(self.config['ball_switches'])

    def wait_for_ready_to_receive(self):
        """Wait until there is at least on inactive switch."""
        # future returns when ball_count != number of switches
        return self.wait_for_ball_count_changes(len(self.config['ball_switches']))

    @asyncio.coroutine
    def wait_for_ball_to_leave(self):
        """Wait for any active switch to become inactive."""
        while True:
            waiter = self.wait_for_count_stable()
            try:
                active_switches = self._count_switches_sync()
                waiter.cancel()
                break
            except ValueError:
                yield from waiter

        waiters = []
        for switch_name in active_switches:
            waiters.append(self.machine.switch_controller.wait_for_switch(
                switch_name=switch_name, state=0))

        if not waiters:
            self.ball_device.log.warning("No switch is active. Cannot wait on empty list.")
            future = asyncio.Future(loop=self.machine.clock.loop)
            future.set_result(True)
            return future

        done_future = Util.ensure_future(Util.first(waiters, self.machine.clock.loop),
                                         loop=self.machine.clock.loop)
        done_future.add_done_callback(self._ball_left)
        return done_future

    def _ball_left(self, future):
        if future.cancelled():
            return
        self._last_count -= 1
        self.record_activity(BallLostActivity())
        self.trigger_recount()
        self.trigger_activity()
