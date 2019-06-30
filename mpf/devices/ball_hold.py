"""Contains the BallHold device class."""
import asyncio
from collections import deque

from mpf.core.enable_disable_mixin import EnableDisableMixin

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("balls_held")
class BallHold(EnableDisableMixin, SystemWideDevice, ModeDevice):

    """Ball hold device which can be used to keep balls in ball devices and control their eject later on."""

    config_section = 'ball_holds'
    collection = 'ball_holds'
    class_label = 'ball_hold'

    __slots__ = ["hold_devices", "source_playfield", "balls_held", "_release_hold", "_released_balls",
                 "hold_queue"]

    def __init__(self, machine, name):
        """Initialise ball hold."""
        self.hold_devices = None
        self.source_playfield = None
        super().__init__(machine, name)

        # initialise variables
        self.balls_held = 0
        self._released_balls = 0
        self._release_hold = None
        self.hold_queue = deque()

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return True

    @classmethod
    def prepare_config(cls, config, is_mode_config):
        """Add default events when outside mode."""
        if not is_mode_config:
            if 'enable_events' not in config:
                config['enable_events'] = 'ball_started'
            if 'disable_events' not in config:
                config['disable_events'] = 'ball_will_end'
        return super().prepare_config(config, is_mode_config)

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        self.hold_devices = []
        for device in self.config['hold_devices']:
            self.hold_devices.append(device)

        if not self.config['balls_to_hold']:
            self.config['balls_to_hold'] = 0

            for device in self.config['hold_devices']:
                self.config['balls_to_hold'] += device.config['ball_capacity']

        self.source_playfield = self.config['source_playfield']

    def _enable(self):
        """Enable the hold.

        If the hold is not enabled, no balls will be held.
        """
        self.debug_log("Enabling...")
        self._register_handlers()

    def _disable(self):
        """Disable the hold.

        If the hold is not enabled, no balls will be held.
        """
        self.debug_log("Disabling...")
        self._unregister_handlers()

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset the hold.

        Will release held balls. Device status will stay the same
        (enabled/disabled). It will wait for those balls to drain and block
        ball_ending until they do. Those balls are not included in ball_in_play.
        """
        self._released_balls += self.release_all()
        self.balls_held = 0

        if self._released_balls > 0:
            # add handler for ball_drain until self._released_balls are drained
            self.machine.events.add_handler(event='ball_drain',
                                            handler=self._wait_for_drain)

            # block ball_ending
            self.machine.events.add_handler(event='ball_ending', priority=10000,
                                            handler=self._block_during_drain)

    def _wait_for_drain(self, balls, **kwargs):
        del kwargs
        if balls <= 0:
            return {'balls': balls}

        if balls > self._released_balls:
            ball_to_reduce = self._released_balls
        else:
            ball_to_reduce = balls

        self._released_balls -= ball_to_reduce
        self.debug_log("%s ball of hold drained.", ball_to_reduce)

        if self._released_balls <= 0:
            if self._release_hold:
                self._release_hold.clear()
                self._release_hold = None
            self.debug_log("All released balls of ball_hold drained.")
            self.machine.events.remove_handler_by_event('ball_ending', self._wait_for_drain)
            self.machine.events.remove_handler_by_event('ball_drain', self._block_during_drain)

        return {'balls': balls - ball_to_reduce}

    def _block_during_drain(self, queue, **kwargs):
        del kwargs
        if self._released_balls > 0:
            queue.wait()
            self._release_hold = queue

    @event_handler(9)
    def event_release_one_if_full(self, **kwargs):
        """Event handler for release_one_if_full event."""
        del kwargs
        self.release_one_if_full()

    def release_one_if_full(self):
        """Release one ball if hold is full."""
        if self.is_full():
            self.release_one()

    @event_handler(8)
    def event_release_one(self, **kwargs):
        """Event handler for release_one event."""
        del kwargs
        self.release_one()

    def release_one(self):
        """Release one ball."""
        self.release_balls(balls_to_release=1)

    @event_handler(7)
    def event_release_all(self, **kwargs):
        """Event handler for release_all event."""
        del kwargs
        self.release_all()

    def release_all(self):
        """Release all balls in hold."""
        return self.release_balls(self.balls_held)

    def release_balls(self, balls_to_release):
        """Release all balls and return the actual amount of balls released.

        Args:
            balls_to_release: number of ball to release from hold
        """
        if not self.hold_queue:
            return 0

        remaining_balls_to_release = balls_to_release

        self.debug_log("Releasing up to %s balls from hold", balls_to_release)
        balls_released = 0
        while self.hold_queue:
            device, balls_held = self.hold_queue.pop()
            balls = balls_held
            balls_in_device = device.balls
            if balls > balls_in_device:
                balls = balls_in_device

            if balls > remaining_balls_to_release:
                self.hold_queue.append(
                    (device, balls_held - remaining_balls_to_release))
                balls = remaining_balls_to_release

            device.eject(balls=balls)
            balls_released += balls
            remaining_balls_to_release -= balls
            if remaining_balls_to_release <= 0:
                break

        if balls_released > 0:
            self.machine.events.post(
                'ball_hold_' + self.name + '_balls_released',
                balls_released=balls_released)
            '''event: ball_hold_(name)_balls_released

            desc: The ball hold device (name) has just released a ball(s).

            args:
                balls_released: The number of balls that were just released.
            '''

        self.balls_held -= balls_released
        return balls_released

    def _register_handlers(self):
        # register on ball_enter of hold_devices
        for device in self.hold_devices:
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_enter',
                self._hold_ball, device=device)

    def _unregister_handlers(self):
        # unregister ball_enter handlers
        self.machine.events.remove_handler(self._hold_ball)

    def is_full(self):
        """Return true if hold is full."""
        return self.remaining_space_in_hold() == 0

    def remaining_space_in_hold(self):
        """Return the remaining capacity of the hold."""
        balls = self.config['balls_to_hold'] - self.balls_held
        if balls < 0:
            balls = 0
        return balls

    def _hold_ball(self, device, new_balls, unclaimed_balls, **kwargs):
        """Handle result of _ball_enter event of hold_devices."""
        del new_balls
        del kwargs
        # if full do not take any balls
        if self.is_full():
            self.debug_log("Cannot hold balls. Hold is full.")
            return {'unclaimed_balls': unclaimed_balls}

        # if there are no balls do not claim anything
        if unclaimed_balls <= 0:
            return {'unclaimed_balls': unclaimed_balls}

        capacity = self.remaining_space_in_hold()
        # take ball up to capacity limit
        if unclaimed_balls > capacity:
            balls_to_hold = capacity
        else:
            balls_to_hold = unclaimed_balls

        self.balls_held += balls_to_hold
        self.debug_log("Held %s balls", balls_to_hold)

        # post event for ball capture
        self.machine.events.post('ball_hold_' + self.name + '_held_ball',
                                 balls_held=balls_to_hold,
                                 total_balls_held=self.balls_held)
        '''event: ball_hold_(name)_held_ball
        desc: The ball hold device (name) has just held additional ball(s).

        args:
            balls_held: The number of new balls just held.
            total_balls_held: The current total number of balls this device
                has held.
        '''

        # check if we are full now and post event if yes
        if self.is_full():
            self.machine.events.post('ball_hold_' + self.name + '_full',
                                     balls=self.balls_held)
        '''event: ball_hold_(name)_full
        desc: The ball hold device (name) is now full.
        args:
            balls: The number of balls currently held in this device.
        '''

        self.hold_queue.append((device, unclaimed_balls))

        return {'unclaimed_balls': unclaimed_balls - balls_to_hold}
