"""Switch ball counter."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.physical_ball_counter import PhysicalBallCounter, BallLostActivity, \
    BallEntranceActivity, UnknownBallActivity, BallReturnActivity


class SwitchCounter(PhysicalBallCounter):

    """Determine ball count by counting switches.

    This should be used for devices with multiple switches and/or a jam switch. Simple devices with only one switch
    should use a simpler counter.
    """

    __slots__ = ["_entrances", "_trigger_recount", "_task", "_is_unreliable", "_switches"]

    def __init__(self, ball_device, config):
        """initialize ball counter."""
        for option in ["entrance_count_delay", "exit_count_delay", "entrance_event_timeout", "jam_switch",
                       "ball_switches"]:
            if option not in config and option in ball_device.config:
                config[option] = ball_device.config[option]
        super().__init__(ball_device, config)

        self.config = self.machine.config_validator.validate_config("ball_device_counter_ball_switches", self.config)
        self._entrances = []
        self._switches = set(self.config['ball_switches'])
        if self.config['jam_switch']:
            self._switches.add(self.config['jam_switch'])
        self._trigger_recount = asyncio.Event()
        # Register switch handlers with delays for entrance & exit counts
        for switch in self._switches:
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=1,
                ms=self.config['entrance_count_delay'],
                callback=self.trigger_recount)
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=1,
                callback=self.invalidate_count)
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=0,
                ms=self.config['exit_count_delay'],
                callback=self.trigger_recount)
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=0,
                callback=self.invalidate_count)

        self._task = asyncio.create_task(self._run())
        self._task.add_done_callback(Util.raise_exceptions)
        self._is_unreliable = False

        # make sure timeouts are reasonable:
        # exit_count_delay < all eject_timeout
        if self.config['exit_count_delay'] > min(
                self.ball_device.config['eject_timeouts'].values()):
            self.ball_device.raise_config_error('Configuration error in {} ball device. '
                                                'all eject_timeouts have to be larger than '
                                                'exit_count_delay'.
                                                format(self.ball_device.name), 6)

        # entrance_count_delay < all eject_timeout
        if self.config['entrance_count_delay'] > min(
                self.ball_device.config['eject_timeouts'].values()):
            self.ball_device.raise_config_error('Configuration error in {} ball device. '
                                                'all eject_timeouts have to be larger than '
                                                'entrance_count_delay'.
                                                format(self.ball_device.name), 7)

        # multiple switches + mechanical eject is not supported
        if (self.capacity > 1 and
                self.ball_device.config['mechanical_eject']):
            self.ball_device.raise_config_error('Configuration error in {} ball device. '
                                                'mechanical_eject can only be used with '
                                                'devices that have 1 ball switch'.
                                                format(self.ball_device.name), 5)

        for switch in self._switches:
            if switch and '{}_active'.format(self.ball_device.config['captures_from'].name) in switch.tags:
                self.ball_device.raise_config_error(
                    "Ball device '{}' uses switch '{}' which has a "
                    "'{}_active' tag. This is handled internally by the device. Remove the "
                    "redundant '{}_active' tag from that switch.".format(
                        self.ball_device.name, switch.name, self.ball_device.config['captures_from'].name,
                        self.ball_device.config['captures_from'].name), 13)

        # cannot have ball switches and capacity
        if self.ball_device.config.get('ball_capacity'):
            self.ball_device.raise_config_error("Cannot use capacity and ball switches.", 3)

    def stop(self):
        """Stop task."""
        super().stop()
        if self._task:
            self._task.cancel()

    def trigger_recount(self):
        """Trigger a count."""
        self._trigger_recount.set()

    async def _recount(self):
        while True:
            await self._trigger_recount.wait()
            self._trigger_recount.clear()
            try:
                balls = self.count_balls_sync()
                return balls
            except ValueError:
                continue

    async def _run(self):
        self._trigger_recount.set()
        while True:
            new_count = await self._recount()
            self.debug_log("SC: New count %s last: %s", new_count, self._last_count)
            self._count_stable.set()

            if self._last_count is None:
                self._last_count = new_count
            elif self._last_count < 0:
                raise AssertionError("Count may never be negative but it {}".format(self._last_count))

            if self.is_jammed() and new_count == 1 and self._last_count != 0:
                # only jam is active. keep previous count
                self.debug_log("SC: Counter is jammed. Only jam is active. Will no longer trust count.")
                # ball potentially returned
                if not self._is_unreliable:
                    self.trigger_activity()
                    self.record_activity(BallReturnActivity())
                    self._is_unreliable = True
                continue

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
            self.debug_log("SC: Updating count to %s", new_count)
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
        for switch in self._switches:
            valid = False
            if self.machine.switch_controller.is_active(
                    switch, ms=self.config['entrance_count_delay']):
                switches.append(switch)
                valid = True
            elif self.machine.switch_controller.is_inactive(
                    switch, ms=self.config['exit_count_delay']):
                valid = True

            if not valid:
                # one of our switches wasn't valid long enough
                self.debug_log("SC: Switch '%s' changed too recently. Aborting count!", switch.name)
                raise ValueError('Count not stable yet. Run again!')

        return switches

    def count_balls_sync(self):
        """Count currently active switches or raise ValueError if switches are unstable."""
        switches = self._count_switches_sync()
        ball_count = len(switches)

        self.debug_log("SC: Counted %s balls. Active switches: %s. Old: %s", ball_count, switches, self._last_count)
        return ball_count

    @property
    def capacity(self):
        """Return capacity under normal circumstances (i.e. without jam switches)."""
        return len(self.config['ball_switches'])

    def is_jammed(self):
        """Return true if the jam switch is currently active."""
        return self.config['jam_switch'] and self.machine.switch_controller.is_active(
            self.config['jam_switch'], ms=self.config['entrance_count_delay'])

    def is_count_unreliable(self):
        """Return true if only the jam switch is active and the count is unknown."""
        return self._is_unreliable

    @property
    def is_ready_to_receive(self):
        """Return true if count is stable and we got at least one slot."""
        try:
            count = len(self._count_switches_sync())
        except ValueError:
            # count not stable
            return False
        # we intentionally do not consider jam_switch here (which would be part of self._switches)
        return count != self.capacity

    async def wait_for_ready_to_receive(self):
        """Wait until there is at least on inactive switch."""
        # future returns when ball_count != number of switches
        # we intentionally do not consider jam_switch here (which would be part of self._switches)
        return await self.wait_for_ball_count_changes(self.capacity)

    async def wait_for_ball_to_leave(self):
        """Wait for any active switch to become inactive."""
        while True:
            waiter = self.wait_for_count_stable()
            try:
                active_switches = self._count_switches_sync()
                waiter.cancel()
                break
            except ValueError:
                await waiter

        waiters = []
        for switch in active_switches:
            waiters.append(self.machine.switch_controller.wait_for_switch(
                switch=switch, state=0))

        if not waiters:
            self.ball_device.log.warning("No switch is active. Cannot wait on empty list.")
            future = asyncio.Future()
            future.set_result(True)
            return future

        done_future = asyncio.ensure_future(Util.first(waiters))
        done_future.add_done_callback(self._ball_left)
        return done_future

    def _ball_left(self, future):
        if future.cancelled():
            return

        self.debug_log("SC: Ball left. Old count: %s", self._last_count)
        if not self._is_unreliable:
            # only do this is count it reliable
            self._last_count -= 1
            self.record_activity(BallLostActivity())
        self.trigger_recount()
        self.trigger_activity()
