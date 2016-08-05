""" Contains the BallLock device class."""

from collections import deque

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("balls_locked", "enabled", "lock_queue")
class BallLock(SystemWideDevice, ModeDevice):
    config_section = 'ball_locks'
    collection = 'ball_locks'
    class_label = 'ball_lock'

    def __init__(self, machine, name):
        self.lock_devices = None
        self.source_playfield = None
        super().__init__(machine, name)

        # initialise variables
        self.balls_locked = 0
        self.enabled = False
        self.lock_queue = deque()

    def device_removed_from_mode(self, mode):
        del mode
        self.disable()

    @classmethod
    def prepare_config(cls, config, is_mode_config):
        if not is_mode_config:
            if 'enable_events' not in config:
                config['enable_events'] = 'ball_started'
            if 'disable_events' not in config:
                config['disable_events'] = 'ball_ending'
        return super().prepare_config(config, is_mode_config)

    def _initialize(self):
        # load lock_devices

        self.lock_devices = []
        for device in self.config['lock_devices']:
            self.lock_devices.append(device)

        self.source_playfield = self.config['source_playfield']

    def enable(self, **kwargs):
        """ Enables the lock. If the lock is not enabled, no balls will be
        locked.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Enabling...")
        if not self.enabled:
            self._register_handlers()
        self.enabled = True

    def disable(self, **kwargs):
        """ Disables the lock. If the lock is not enabled, no balls will be
        locked.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Disabling...")
        self._unregister_handlers()
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the lock. Will release locked balls. Device will status will
        stay the same (enabled/disabled)

        Args:
            **kwargs: unused
        """
        del kwargs
        self.release_all_balls()
        self.balls_locked = 0

    def release_one(self, **kwargs):
        """ Releases one ball

        Args:
            **kwargs: unused
        """
        del kwargs
        self.release_balls(balls_to_release=1)

    def release_all_balls(self):
        """ Releases all balls in lock

        """
        self.release_balls(self.balls_locked)

    def release_balls(self, balls_to_release):
        """Release all balls and return the actual amount of balls released.

        Args:
            balls_to_release: number of ball to release from lock
        """
        if len(self.lock_queue) == 0:
            return 0

        remaining_balls_to_release = balls_to_release

        self.log.debug("Releasing up to %s balls from lock", balls_to_release)
        balls_released = 0
        while len(self.lock_queue) > 0:
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

    # return true if lock is full
    def is_full(self):
        return self.remaining_space_in_lock() == 0

    # return the remaining capacity of the lock
    def remaining_space_in_lock(self):
        balls = self.config['balls_to_lock'] - self.balls_locked
        if balls < 0:
            balls = 0
        return balls

    # callback for _ball_enter event of lock_devices
    def _lock_ball(self, device, new_balls, unclaimed_balls, **kwargs):
        del new_balls
        del kwargs
        # if full do not take any balls
        if self.is_full():
            self.log.debug("Cannot lock balls. Lock is full.")
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
        self.log.debug("Locked %s balls", balls_to_lock)

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
        self.request_new_balls(balls_to_lock)

        return {'unclaimed_balls': unclaimed_balls - balls_to_lock}

    def request_new_balls(self, balls):
        if self.config['request_new_balls_to_pf']:
            self.source_playfield.add_ball(balls=balls)
