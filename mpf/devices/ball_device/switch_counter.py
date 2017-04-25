"""Switch ball counter."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_count_handler import EjectTracker
from mpf.devices.ball_device.ball_device_ball_counter import BallDeviceBallCounter


class SwitchCounter(BallDeviceBallCounter):

    """Determine ball count by counting switches.

    This should be used for devices with multiple switches and/or a jam switch. Simple devices with only one switch
    should use a simpler counter.
    """

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

        self.debug_log("Counted %s balls. Active switches: %s", ball_count, switches)
        return ball_count

    def wait_for_ball_activity(self):
        """Wait for ball count changes."""
        future = asyncio.Future(loop=self.machine.clock.loop)
        self._futures.append(future)
        return future

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
            waiter = self.wait_for_ball_activity()
            try:
                active_switches = self._count_switches_sync()
                waiter.cancel()
                break
            except ValueError:
                yield from waiter

        ball_left_future = Util.ensure_future(self._wait_for_ball_to_leave(active_switches),
                                              loop=self.machine.clock.loop) if not already_left else None

        # all switches are stable. we are ready now
        eject_tracker.set_ready()

        jam_active_before_eject = self.is_jammed()
        jam_active_after_eject = False
        active_switches = active_switches
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
                    # TODO: add some magic to detect entrances
                    pass
                if new_count > count:
                    eject_tracker.track_unknown_balls(new_count - count)
                elif count > new_count:
                    eject_tracker.track_lost_balls(count - new_count)
                count = new_count

    def _wait_for_ball_to_leave(self, active_switches):
        """Wait for any active switch to become inactive."""
        waiters = []
        for switch_name in active_switches:
            waiters.append(self.machine.switch_controller.wait_for_switch(
                switch_name=switch_name, state=0))

        if not waiters:
            # TODO: raise exception and handle this in ball_device
            self.ball_device.log.warning("No switch is active. Cannot wait on empty list.")
            future = asyncio.Future(loop=self.machine.clock.loop)
            future.set_result(True)
            return future

        return Util.first(waiters, self.machine.clock.loop)
