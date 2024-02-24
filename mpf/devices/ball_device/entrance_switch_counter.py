"""Count balls using an entrance switch."""
import asyncio

from mpf.core.delays import DelayManager
from mpf.devices.ball_device.physical_ball_counter import PhysicalBallCounter, BallEntranceActivity, \
    BallLostActivity


class EntranceSwitchCounter(PhysicalBallCounter):

    """Count balls using an entrance switch."""

    __slots__ = ["recycle_secs", "recycle_clear_time", "_settle_delay"]

    def __init__(self, ball_device, config):
        """initialize entrance switch counter."""
        for option in ["entrance_switch", "entrance_switch_ignore_window_ms", "entrance_switch_full_timeout",
                       "ball_capacity"]:
            if option not in config and option in ball_device.config:
                config[option] = ball_device.config[option]
        super().__init__(ball_device, config)
        self._settle_delay = DelayManager(self.machine)

        self.config = self.machine.config_validator.validate_config("ball_device_counter_entrance_switches",
                                                                    self.config)

        self.recycle_secs = self.config['entrance_switch_ignore_window_ms'] / 1000.0
        self.recycle_clear_time = {}

        for switch in self.config['entrance_switch']:
            # Configure switch handlers for entrance switch activity
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=1,
                ms=0,
                callback=self._entrance_switch_handler,
                callback_kwargs={"switch_name": switch.name})

            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=0,
                ms=0,
                callback=self._entrance_switch_released_handler,
                callback_kwargs={"switch_name": switch.name})

        if self.config['entrance_switch_full_timeout'] and self.config['ball_capacity']:
            if len(self.config['entrance_switch']) > 1:
                raise AssertionError("entrance_switch_full_timeout not supported with multiple entrance switches.")
            self.machine.switch_controller.add_switch_handler_obj(
                switch=self.config['entrance_switch'][0], state=1,
                ms=self.config['entrance_switch_full_timeout'],
                callback=self._entrance_switch_full_handler)

        # Handle initial ball count with entrance_switch. If there is a ball on the entrance_switch at boot
        # assume that we are at max capacity.
        if (self.config['ball_capacity'] and self.config['entrance_switch_full_timeout'] and
                self.machine.switch_controller.is_active(self.config['entrance_switch'][0],
                                                         ms=self.config['entrance_switch_full_timeout'])):
            self._last_count = self.config['ball_capacity']
        else:
            self._last_count = 0
        self._count_stable.set()

        # TODO validate that we are not used with mechanical eject
        if not self.config['ball_capacity']:
            self.ball_device.raise_config_error("Need ball capacity if there are no switches.", 2)
        elif self.ball_device.config.get('ball_switches'):
            self.ball_device.raise_config_error("Cannot use capacity and ball switches.", 3)

    @property
    def capacity(self):
        """Return capacity under normal circumstances (i.e. without jam switches)."""
        return self.config['ball_capacity']

    def is_jammed(self) -> bool:
        """Return False because this device can not know if it is jammed."""
        return False

    def is_count_unreliable(self) -> bool:
        """Return False because this device can not know if it is jammed."""
        return False

    def received_entrance_event(self):
        """Handle entrance event."""
        self._entrance_switch_handler("event")

    def _recycle_passed(self, switch):
        self.recycle_clear_time[switch] = None

    def _entrance_switch_handler(self, switch_name):
        """Add a ball to the device since the entrance switch has been hit."""
        # always invalidate count if this has been triggered by a real switch
        if switch_name != "event":
            self.invalidate_count()
        # If recycle is ongoing, do nothing
        if self.recycle_clear_time.get(switch_name, False):
            self.debug_log("Entrance switch hit within ignore window, taking no action")
            return
        # If a recycle time is configured, set a timeout to prevent future entrance activity
        if self.recycle_secs:
            self.recycle_clear_time[switch_name] = self.machine.clock.get_time() + self.recycle_secs
            self.machine.clock.loop.call_at(self.recycle_clear_time[switch_name], self._recycle_passed, switch_name)

        self.debug_log("Entrance switch hit")
        if self.config['ball_capacity'] and self.config['ball_capacity'] <= self._last_count:
            # do not count beyond capacity
            self.ball_device.log.warning("Device received balls but is already full!")
        elif self.config['ball_capacity'] and self.config['entrance_switch_full_timeout'] and \
                self.config['ball_capacity'] == self._last_count + 1:
            # wait for entrance_switch_full_timeout before setting the device to full capacity
            self._settle_delay.remove("count_stable")
        else:
            # increase count
            self._settle_delay.reset(self.config['settle_time_ms'], self.mark_count_as_stable_and_trigger_activity,
                                     "count_stable")
            self._last_count += 1
            self.record_activity(BallEntranceActivity())

    def _entrance_switch_released_handler(self, switch_name):
        """Entrance switch has been released."""
        del switch_name
        # count is stable once switch is inactive
        # (or if it stays on the switch long enough; see _entrance_switch_full_handler)
        self._count_stable.set()

    def _entrance_switch_full_handler(self):
        # a ball is sitting on the entrance_switch. assume the device is full
        self._count_stable.set()
        new_balls = self.config['ball_capacity'] - self._last_count
        self.mark_count_as_stable_and_trigger_activity()
        if new_balls > 0:
            self.debug_log("Ball is sitting on entrance_switch. Assuming "
                           "device is full. Adding %s balls and setting balls"
                           "to %s", new_balls, self.config['ball_capacity'])
            self._last_count += new_balls
            for _ in range(new_balls):
                self.record_activity(BallEntranceActivity())

    def count_balls_sync(self) -> int:
        """Return the number of balls entered."""
        assert self._last_count is not None
        if self.config['ball_capacity'] and self.config['ball_capacity'] == self._last_count:
            # we are at capacity. this is fine
            pass
        elif self.config['ball_capacity'] and self.config['entrance_switch_full_timeout'] and \
            self.config['ball_capacity'] == self._last_count + 1 and \
            self.machine.switch_controller.is_active(self.config['entrance_switch'][0],
                                                     ms=self.config['entrance_switch_full_timeout']):
            # can count when entrance switch is active for at least entrance_switch_full_timeout
            pass
        elif not self.is_ready_to_receive:
            # cannot count when the entrance_switch is still active
            raise ValueError

        return self._last_count

    async def wait_for_ball_to_leave(self):
        """Wait for a ball to leave."""
        await self.wait_for_count_stable()
        # wait 10ms
        done_future = asyncio.ensure_future(asyncio.sleep(0.01))
        done_future.add_done_callback(self._ball_left)
        return done_future

    def _ball_left(self, future):
        del future
        self._last_count -= 1
        self.record_activity(BallLostActivity())
        self.trigger_activity()

    @property
    def is_ready_to_receive(self):
        """Return true if entrance switch is inactive."""
        return not all(self.machine.switch_controller.is_active(switch) for switch in self.config['entrance_switch'])

    async def wait_for_ready_to_receive(self):
        """Wait until all entrance switch are inactive."""
        while True:
            if self.is_ready_to_receive:
                return True

            await self.machine.switch_controller.wait_for_any_switch(
                switches=self.config['entrance_switch'],
                state=0, only_on_change=True)
