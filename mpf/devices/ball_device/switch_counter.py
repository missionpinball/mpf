"""Switch ball counter."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_ball_counter import PhysicalBallCounter, EjectTracker, BallLostActivity, \
    BallEntranceActivity, UnknownBallActivity


class SwitchCounter(PhysicalBallCounter):

    """Determine ball count by counting switches.

    This should be used for devices with multiple switches and/or a jam switch. Simple devices with only one switch
    should use a simpler counter.
    """

    def __init__(self, ball_device, config):
        """Initialise ball counter."""
        super().__init__(ball_device, config)
        self._entrances = []
        self._trigger_recount = asyncio.Event(loop=self.machine.clock.loop)
        # TODO: use ball_switches and jam_switch!
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

        self.machine.clock.loop.create_task(self._run())

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
            else:
                # count did not change
                continue
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

    def wait_for_ready_to_receive(self):
        """Wait until there is at least on inactive switch."""
        # future returns when ball_count != number of switches
        return self.wait_for_ball_count_changes(len(self.config['ball_switches']))

    @asyncio.coroutine
    def track_eject(self, eject_tracker: EjectTracker, already_left):
        """Return eject_process dict."""
        # count active switches
        while True:
            waiter = self.wait_for_count_stable()
            try:
                active_switches = self._count_switches_sync()
                waiter.cancel()
                break
            except ValueError:
                yield from waiter

        ball_left_future = Util.ensure_future(self.wait_for_ball_to_leave(),
                                              loop=self.machine.clock.loop) if not already_left else None

        # all switches are stable. we are ready now
        eject_tracker.set_ready()

        jam_active_before_eject = self.is_jammed()
        jam_active_after_eject = False
        count = len(active_switches)
        while True:
            ball_count_change = Util.ensure_future(self.wait_for_ball_count_changes(count),
                                                   loop=self.machine.clock.loop)
            if ball_left_future:
                futures = [ball_count_change, ball_left_future]
            else:
                futures = [ball_count_change]
            yield from Util.any(futures, loop=self.machine.clock.loop)

            if ball_left_future and ball_left_future.done():
                ball_left_future = None
                eject_tracker.track_ball_left()
                count -= 1
                ball_count_change.cancel()
            elif ball_count_change.done():
                new_count = ball_count_change.result()
                # check jam first
                if not jam_active_after_eject and not jam_active_before_eject and self.is_jammed():
                    eject_tracker.track_ball_returned()
                    jam_active_after_eject = True
                    count += 1
                if new_count > count:
                    for _ in range(new_count - count):
                        try:
                            last_entrance = self._entrances.pop(0)
                        except IndexError:
                            last_entrance = -1000

                        if last_entrance > self.machine.clock.get_time() - self.config['entrance_event_timeout']:
                            eject_tracker.track_ball_entrance()
                        else:
                            eject_tracker.track_unknown_balls(1)
                elif count > new_count:
                    eject_tracker.track_lost_balls(count - new_count)
                count = new_count

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
