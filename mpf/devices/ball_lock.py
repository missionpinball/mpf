"""Contains the BallLock device class."""
import asyncio
from collections import deque

from mpf.core.events import event_handler

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("balls_locked", "enabled", "lock_queue")
class BallLock(SystemWideDevice, ModeDevice):

    """Ball lock device which can be used to keep balls in ball devices and control their eject later on."""

    config_section = 'ball_locks'
    collection = 'ball_locks'
    class_label = 'ball_lock'

    __slots__ = ["lock_devices", "source_playfield", "balls_locked", "enabled", "_released_balls", "_release_lock",
                 "lock_queue"]

    def __init__(self, machine, name):
        """Initialise ball lock."""
        self.lock_devices = None
        self.source_playfield = None
        super().__init__(machine, name)

        # initialise variables
        self.balls_locked = 0
        self.enabled = False
        self._released_balls = 0
        self._release_lock = None
        self.lock_queue = deque()

    def device_removed_from_mode(self, mode):
        """Disable ball lock when mode ends."""
        del mode
        self.disable()

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
        # load lock_devices
        self.lock_devices = []
        for device in self.config['lock_devices']:
            self.lock_devices.append(device)

        self.source_playfield = self.config['source_playfield']

    def enable(self):
        """Enable the lock.

        If the lock is not enabled, no balls will be locked.
        """
        self.debug_log("Enabling...")
        super().enable()
        if not self.enabled:
            self._register_handlers()
        self.enabled = True

    @event_handler(0)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable the lock.

        If the lock is not enabled, no balls will be locked.
        """
        self.debug_log("Disabling...")
        self._unregister_handlers()
        self.enabled = False

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset the lock.

        Will release locked balls. Device will status will stay the same (enabled/disabled). It will wait for those
        balls to drain and block ball_ending until they did. Those balls are not included in ball_in_play.
        """
        self._released_balls += self.release_all_balls()
        self.balls_locked = 0

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
        self.debug_log("%s ball of lock drained.", ball_to_reduce)

        if self._released_balls <= 0:
            if self._release_lock:
                self._release_lock.clear()
                self._release_lock = None
            self.debug_log("All released balls of lock drained.")
            self.machine.events.remove_handler_by_event('ball_ending', self._wait_for_drain)
            self.machine.events.remove_handler_by_event('ball_drain', self._block_during_drain)

        return {'balls': balls - ball_to_reduce}

    def _block_during_drain(self, queue, **kwargs):
        del kwargs
        if self._released_balls > 0:
            queue.wait()
            self._release_lock = queue

    @event_handler(9)
    def event_release_one_if_full(self, **kwargs):
        """Event handler for release_one_if_full event."""
        del kwargs
        self.release_one_if_full()

    def release_one_if_full(self):
        """Release one ball if lock is full."""
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
    def event_release_all_balls(self, **kwargs):
        """Event handler for release_all_balls event."""
        del kwargs
        self.release_all_balls()

    def release_all_balls(self):
        """Release all balls in lock."""
        return self.release_balls(self.balls_locked)

    def release_balls(self, balls_to_release):
        """Release all balls and return the actual amount of balls released.

        Args:
            balls_to_release: number of ball to release from lock
        """
        if not self.lock_queue:
            return 0

        remaining_balls_to_release = balls_to_release

        self.debug_log("Releasing up to %s balls from lock", balls_to_release)
        balls_released = 0
        while self.lock_queue:
            device, balls_locked = self.lock_queue.pop()
            balls = balls_locked
            balls_in_device = device.balls
            if balls > balls_in_device:
                balls = balls_in_device

            if balls > remaining_balls_to_release:
                self.lock_queue.append(
                    (device, balls_locked - remaining_balls_to_release))
                balls = remaining_balls_to_release

            device.eject(balls=balls)
            balls_released += balls
            remaining_balls_to_release -= balls
            if remaining_balls_to_release <= 0:
                break

        if balls_released > 0:
            self.machine.events.post(
                'ball_lock_' + self.name + '_balls_released',
                balls_released=balls_released)
            '''event: ball_lock_(name)_balls_released

            desc: The ball lock device (name) has just released a ball(s).

            args:
                balls_released: The number of balls that were just released.
            '''

        self.balls_locked -= balls_released
        return balls_released

    def _register_handlers(self):
        # register on ball_enter of lock_devices
        for device in self.lock_devices:
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_enter',
                self._lock_ball, device=device)

    def _unregister_handlers(self):
        # unregister ball_enter handlers
        self.machine.events.remove_handler(self._lock_ball)

    def is_full(self):
        """Return true if lock is full."""
        return self.remaining_space_in_lock() == 0

    def remaining_space_in_lock(self):
        """Return the remaining capacity of the lock."""
        balls = self.config['balls_to_lock'] - self.balls_locked
        if balls < 0:
            balls = 0
        return balls

    def _lock_ball(self, device, new_balls, unclaimed_balls, **kwargs):
        """Handle result of _ball_enter event of lock_devices."""
        del new_balls
        del kwargs
        # if full do not take any balls
        if self.is_full():
            self.debug_log("Cannot lock balls. Lock is full.")
            return {'unclaimed_balls': unclaimed_balls}

        # if there are no balls do not claim anything
        if unclaimed_balls <= 0:
            return {'unclaimed_balls': unclaimed_balls}

        capacity = self.remaining_space_in_lock()
        # take ball up to capacity limit
        if unclaimed_balls > capacity:
            balls_to_lock = capacity
        else:
            balls_to_lock = unclaimed_balls

        self.balls_locked += balls_to_lock
        self.debug_log("Locked %s balls", balls_to_lock)

        # post event for ball capture
        self.machine.events.post('ball_lock_' + self.name + '_locked_ball',
                                 balls_locked=balls_to_lock,
                                 total_balls_locked=self.balls_locked)
        '''event: ball_lock_(name)_locked_ball
        desc: The ball lock device (name) has just locked additional ball(s).

        args:
            balls_locked: The number of new balls just locked.
            total_balls_locked: The current total number of balls this device
                has locked.
        '''

        # check if we are full now and post event if yes
        if self.is_full():
            self.machine.events.post('ball_lock_' + self.name + '_full',
                                     balls=self.balls_locked)
        '''event: ball_lock_(name)_full
        desc: The ball lock device (name) is now full.
        args:
            balls: The number of balls currently locked in this device.
        '''

        self.lock_queue.append((device, unclaimed_balls))

        # schedule eject of new balls
        self._request_new_balls(balls_to_lock)

        return {'unclaimed_balls': unclaimed_balls - balls_to_lock}

    def _request_new_balls(self, balls):
        """Request new ball to playfield."""
        if self.config['request_new_balls_to_pf']:
            self.source_playfield.add_ball(balls=balls)
