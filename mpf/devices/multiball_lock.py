"""Contains the BallLock device class."""
import asyncio

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.mode_device import ModeDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.ball_device.ball_device import BallDevice


@DeviceMonitor("enabled", "locked_balls")
class MultiballLock(ModeDevice):

    """Ball lock device which locks balls for a multiball."""

    config_section = 'multiball_locks'
    collection = 'multiball_locks'
    class_label = 'multiball_lock'

    __slots__ = ["lock_devices", "source_playfield", "enabled", "_events", "_locked_balls"]

    def __init__(self, machine, name):
        """Initialise ball lock."""
        self.lock_devices = []
        self.source_playfield = None

        # initialise variables
        self.enabled = False
        self._events = {}

        self._locked_balls = 0
        # Locked balls in case we are keep_virtual_ball_count_per_player is false

        super().__init__(machine, name)

    def device_removed_from_mode(self, mode):
        """Disable ball lock when mode ends."""
        del mode
        self.disable()

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return False

    @asyncio.coroutine
    def _initialize(self):
        # load lock_devices
        yield from super()._initialize()

        self.lock_devices = []
        for device in self.config['lock_devices']:
            self.lock_devices.append(device)
            self._events[device] = []

        self.source_playfield = self.config['source_playfield']

        self.machine.events.add_handler("player_turn_starting", self._player_turn_starting)

    @event_handler(10)
    def enable(self, **kwargs):
        """Enable the lock.

        If the lock is not enabled, no balls will be locked.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.debug_log("Enabling...")
        if not self.enabled:
            self._register_handlers()
        self.enabled = True

    def _player_turn_starting(self, queue, **kwargs):
        del kwargs
        # reset locked balls
        self._locked_balls = 0

        # check if the lock is physically full and not virtually full and release balls in that case
        if self._physically_remaining_space <= 0 and not self.is_virtually_full:
            self.log.info("Will release a ball because the lock is phyiscally full but not virtually for the player.")
            # TODO: eject to next playfield
            self.lock_devices[0].eject()
            queue.wait()
            self.machine.events.add_handler("ball_drain", self._wait_for_drain, queue=queue)

    def _wait_for_drain(self, queue, balls, **kwargs):
        del kwargs
        if balls <= 0:
            return {'balls': balls}

        self.debug_log("Ball of lock drained.")

        queue.clear()

        self.machine.events.remove_handler_by_event('ball_drain', self._wait_for_drain)

        return {'balls': balls - 1}

    @event_handler(0)
    def disable(self, **kwargs):
        """Disable the lock.

        If the lock is not enabled, no balls will be locked.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.debug_log("Disabling...")
        self._unregister_handlers()
        self.enabled = False

    @event_handler(1)
    def reset_all_counts(self, **kwargs):
        """Reset the locked balls for all players."""
        del kwargs
        if self.config['locked_ball_counting_strategy'] not in ("virtual_only", "min_virtual_physical"):
            raise AssertionError("Count is only tracked per player")
        for player in self.machine.game.player_list:
            player['{}_locked_balls'.format(self.name)] = 0

    @event_handler(2)
    def reset_count_for_current_player(self, **kwargs):
        """Reset the locked balls for the current player."""
        del kwargs
        if self.config['locked_ball_counting_strategy'] in ("virtual_only", "min_virtual_physical"):
            self.machine.game.player['{}_locked_balls'.format(self.name)] = 0
        elif self.config['locked_ball_counting_strategy'] == "no_virtual":
            self._locked_balls = 0
        else:
            raise AssertionError("Cannot reset physical balls")

    @property
    def locked_balls(self):
        """Return the number of locked balls for the current player."""
        if not self.machine.game:
            # this is required for the monitor because it will query this variable outside of a game
            # remove when #893 is fixed
            return None

        if self.config['locked_ball_counting_strategy'] == "virtual_only":
            return self.machine.game.player['{}_locked_balls'.format(self.name)]
        elif self.config['locked_ball_counting_strategy'] == "min_virtual_physical":
            return min(self.machine.game.player['{}_locked_balls'.format(self.name)], self._physically_locked_balls)
        elif self.config['locked_ball_counting_strategy'] == "physical_only":
            return self._physically_locked_balls
        else:
            return self._locked_balls

    @locked_balls.setter
    def locked_balls(self, value):
        """Set the number of locked balls for the current player."""
        if self.config['locked_ball_counting_strategy'] in ("virtual_only", "min_virtual_physical"):
            self.machine.game.player['{}_locked_balls'.format(self.name)] = value
        elif self.config['locked_ball_counting_strategy'] in "no_virtual":
            self._locked_balls = value

    def _register_handlers(self):
        # register on ball_enter of lock_devices
        for device in self.lock_devices:
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_enter',
                self._lock_ball, device=device, priority=self.mode.priority)
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_entered',
                self._post_events, device=device, priority=self.mode.priority)

    def _unregister_handlers(self):
        # unregister ball_enter handlers
        self.machine.events.remove_handler(self._lock_ball)
        self.machine.events.remove_handler(self._post_events)

    @property
    def is_virtually_full(self):
        """Return true if lock is full."""
        return self.remaining_virtual_space_in_lock <= 0

    @property
    def remaining_virtual_space_in_lock(self):
        """Return the remaining capacity of the lock."""
        balls = self.config['balls_to_lock'] - self.locked_balls
        if balls < 0:
            balls = 0
        return balls

    @property
    def _max_balls_locked_by_any_player(self):
        """Return the highest number of balls locked for all players."""
        max_balls = 0
        for player in self.machine.game.player_list:
            if max_balls < player['{}_locked_balls'.format(self.name)]:
                max_balls = player['{}_locked_balls'.format(self.name)]

        return max_balls

    @property
    def _physically_locked_balls(self):
        """Return the number of physically locked balls."""
        balls = 0
        for device in self.lock_devices:
            balls += device.available_balls

        return balls

    @property
    def _physically_remaining_space(self):
        """Return the space in the physically locks."""
        balls = 0
        for device in self.lock_devices:
            balls += device.capacity - device.available_balls

        return balls

    def _lock_ball(self, unclaimed_balls: int, new_available_balls: int, device: "BallDevice", **kwargs):
        """Handle result of the _ball_enter event of lock_devices."""
        del kwargs
        # if full do not take any balls
        if self.is_virtually_full:
            self.debug_log("Cannot lock balls. Lock is full.")
            return {'unclaimed_balls': unclaimed_balls}

        # if there are no balls do not claim anything
        if unclaimed_balls <= 0:
            return {'unclaimed_balls': unclaimed_balls}

        capacity = self.remaining_virtual_space_in_lock
        # take ball up to capacity limit
        if unclaimed_balls > capacity:
            balls_to_lock = capacity
        else:
            balls_to_lock = unclaimed_balls

        balls_to_lock_physically = balls_to_lock

        for _ in range(balls_to_lock):
            self.locked_balls += 1
            # post event for ball capture
            self._events[device].append({"event": 'multiball_lock_' + self.name + '_locked_ball',
                                         "total_balls_locked": self.locked_balls})
            '''event: multiball_lock_(name)_locked_ball
            desc: The multiball lock device (name) has just locked one additional ball.

            args:
                total_balls_locked: The current total number of balls this device
                    has locked.
            '''

        if self.config['locked_ball_counting_strategy'] in ("virtual_only", "min_virtual_physical"):
            # only keep ball if any player could use it
            if self._max_balls_locked_by_any_player < self._physically_locked_balls + new_available_balls:
                balls_to_lock_physically = 0

        if self.config['locked_ball_counting_strategy'] == "min_virtual_physical":
            # do not lock if the lock would be physically full but not virtually
            if (self._physically_remaining_space <= 1 and
                    self.config['balls_to_lock'] - self.machine.game.player['{}_locked_balls'.format(self.name)] > 0):
                balls_to_lock_physically = 0
        elif self.config['locked_ball_counting_strategy'] != "physical_only":
            # do not lock if the lock would be physically full but not virtually
            if not self.is_virtually_full and self._physically_remaining_space <= 1:
                balls_to_lock_physically = 0

        # check if we are full now and post event if yes
        if self.is_virtually_full:
            self._events[device].append({'event': 'multiball_lock_' + self.name + '_full',
                                         'balls': self.locked_balls})
        '''event: multiball_lock_(name)_full
        desc: The multiball lock device (name) is now full.
        args:
            balls: The number of balls currently locked in this device.
        '''

        # schedule eject of new balls for all physically locked balls
        if self.config['balls_to_replace'] == -1 or self.locked_balls <= self.config['balls_to_replace']:
            self.debug_log("{} locked balls and {} to replace, requesting {} new balls"
                           .format(self.locked_balls, self.config['balls_to_replace'], balls_to_lock_physically))
            self._request_new_balls(balls_to_lock_physically)
        else:
            self.debug_log("{} locked balls exceeds {} to replace, not requesting any balls"
                           .format(self.locked_balls, self.config['balls_to_replace']))

        self.debug_log("Locked %s balls virtually and %s balls physically", balls_to_lock, balls_to_lock_physically)

        return {'unclaimed_balls': unclaimed_balls - balls_to_lock_physically}

    def _post_events(self, device, **kwargs):
        """Post events on callback from _ball_entered handler.

        Events are delayed to this handler because we want the ball device to have accounted for the balls.
        """
        del kwargs
        for event in self._events[device]:
            self.machine.events.post(**event)
        self._events[device] = []

    def _request_new_balls(self, balls):
        """Request new ball to playfield."""
        self.source_playfield.add_ball(balls=balls)
