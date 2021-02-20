"""Contains the BallLock device class."""
from typing import List, Optional

from mpf.core.enable_disable_mixin import EnableDisableMixin

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.mode_device import ModeDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.ball_device.ball_device import BallDevice  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.playfield import Playfield     # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor("locked_balls")
class MultiballLock(EnableDisableMixin, ModeDevice):

    """Ball lock device which locks balls for a multiball."""

    config_section = 'multiball_locks'
    collection = 'multiball_locks'
    class_label = 'multiball_lock'

    __slots__ = ["lock_devices", "source_playfield", "_events", "_locked_balls", "_source_devices"]

    def __init__(self, machine, name):
        """Initialise ball lock."""
        self.lock_devices = []
        self.source_playfield = None    # type: Optional[Playfield]
        self._source_devices = None     # type: Optional[List[BallDevice]]

        # initialise variables
        self._events = {}

        self._locked_balls = 0
        # Locked balls in case we are keep_virtual_ball_count_per_player is false

        super().__init__(machine, name)

    async def _initialize(self):
        # load lock_devices
        await super()._initialize()

        self.lock_devices = []
        for device in self.config['lock_devices']:
            self.lock_devices.append(device)
            self._events[device] = []

        self.source_playfield = self.config['source_playfield']
        self._source_devices = self.config['source_devices']

        self.machine.events.add_handler("player_turn_starting", self._player_turn_starting)

    def _enable(self):
        """Enable the lock.

        If the lock is not enabled, no balls will be locked.
        """
        self.debug_log("Enabling...")
        self._register_handlers()

    def _player_turn_starting(self, queue, **kwargs):
        del kwargs
        # reset locked balls
        self._locked_balls = 0

        # check if the lock is physically full and not virtually full and release balls in that case
        if self._physically_remaining_space <= 0 and not self.is_virtually_full:
            self.log.info("Will release a ball because the lock is physically full but not virtually for the player.")
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

    def _disable(self):
        """Disable the lock.

        If the lock is not enabled, no balls will be locked.
        """
        self.debug_log("Disabling...")
        self._unregister_handlers()

    @event_handler(1)
    def event_reset_all_counts(self, **kwargs):
        """Event handler for reset_all_counts event."""
        del kwargs
        self.reset_all_counts()

    def reset_all_counts(self):
        """Reset the locked balls for all players."""
        if self.config['locked_ball_counting_strategy'] not in ("virtual_only", "min_virtual_physical"):
            raise AssertionError("Count is only tracked per player")
        for player in self.machine.game.player_list:
            player['{}_locked_balls'.format(self.name)] = 0

    @event_handler(2)
    def event_reset_count_for_current_player(self, **kwargs):
        """Event handler for reset_count_for_current_player event."""
        del kwargs
        self.reset_count_for_current_player()

    def reset_count_for_current_player(self):
        """Reset the locked balls for the current player."""
        if self.config['locked_ball_counting_strategy'] in ("virtual_only", "min_virtual_physical", "no_virtual"):
            self.locked_balls = 0
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
        if self.config['locked_ball_counting_strategy'] == "min_virtual_physical":
            return min(self.machine.game.player['{}_locked_balls'.format(self.name)], self._physically_locked_balls)
        if self.config['locked_ball_counting_strategy'] == "physical_only":
            return self._physically_locked_balls

        return self._locked_balls

    @locked_balls.setter
    def locked_balls(self, value):
        """Set the number of locked balls for the current player."""
        if self.config['locked_ball_counting_strategy'] in ("virtual_only", "min_virtual_physical"):
            self.machine.game.player['{}_locked_balls'.format(self.name)] = value
        elif self.config['locked_ball_counting_strategy'] in "no_virtual":
            self._locked_balls = value
        else:
            raise AssertionError("Cannot write locked_balls for strategy {}".format(
                self.config['locked_ball_counting_strategy']))

    def _register_handlers(self):
        priority = (self.mode.priority if self.mode else 0) + \
            self.config['priority']
        # register on ball_enter of lock_devices
        for device in self.lock_devices:
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_enter',
                self._lock_ball, device=device, priority=priority)
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_entered',
                self._post_events, device=device, priority=priority)

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
        # if there are no balls do not claim anything
        if unclaimed_balls <= 0:
            return {'unclaimed_balls': unclaimed_balls}

        # MPF will make sure that devices get one event per ball
        assert unclaimed_balls == 1

        if not self.machine.game or not self.machine.game.player:
            # bail out if we are outside of a game
            return {'unclaimed_balls': unclaimed_balls}

        # if already full do not take any balls
        if self.is_virtually_full:
            self.debug_log("Cannot lock balls. Lock is full.")
            return {'unclaimed_balls': unclaimed_balls}

        # first take care of virtual ball count in lock
        capacity = self.remaining_virtual_space_in_lock
        # take ball up to capacity limit
        if unclaimed_balls > capacity:
            balls_to_lock = capacity
        else:
            balls_to_lock = unclaimed_balls

        new_locked_balls = self.locked_balls + 1
        # post event for ball capture
        self._events[device].append({"event": 'multiball_lock_' + self.name + '_locked_ball',
                                     "total_balls_locked": new_locked_balls})
        '''event: multiball_lock_(name)_locked_ball
        desc: The multiball lock device (name) has just locked one additional ball.

        args:
            total_balls_locked: The current total number of balls this device
                has locked.
        '''
        if self.config['locked_ball_counting_strategy'] != "physical_only":
            self.locked_balls = new_locked_balls

        # now check how many balls we want physically in the lock
        balls_to_lock_physically = balls_to_lock

        if self._physically_remaining_space < new_available_balls:
            # we cannot lock if there isn't any space left
            balls_to_lock_physically = 0
            self.debug_log("Will not keep the ball. Device is full. Remaining space: %s. Balls to lock: %s",
                           self._physically_remaining_space, balls_to_lock)

        if self.config['locked_ball_counting_strategy'] in ("virtual_only", "min_virtual_physical"):
            # only keep ball if any player could use it
            if self._max_balls_locked_by_any_player < self._physically_locked_balls + new_available_balls:
                self.debug_log("Will not keep ball because no player could use it. Max locked balls by any player "
                               "is %s and we physically got %s", self._max_balls_locked_by_any_player,
                               self._physically_locked_balls)
                balls_to_lock_physically = 0

        if self.config['locked_ball_counting_strategy'] == "min_virtual_physical":
            # do not lock if the lock would be physically full but not virtually
            if (self._physically_remaining_space <= new_available_balls and
                    self.config['balls_to_lock'] - self.machine.game.player['{}_locked_balls'.format(self.name)] > 0):
                self.debug_log("Will not keep ball because the lock would be physically full but virtually still "
                               "has space for this player.")
                balls_to_lock_physically = 0
        elif self.config['locked_ball_counting_strategy'] != "physical_only":
            # do not lock if the lock would be physically full but not virtually
            if not self.is_virtually_full and self._physically_remaining_space <= new_available_balls:
                balls_to_lock_physically = 0
                self.debug_log("Will not keep ball because the lock would be physically full but virtually still "
                               "has space for this player.")

        # check if we are full now and post event if yes
        if (self.config['locked_ball_counting_strategy'] == "physical_only" and
            new_locked_balls >= self.config['balls_to_lock']) or \
                self.remaining_virtual_space_in_lock == 0:
            self._events[device].append({'event': 'multiball_lock_' + self.name + '_full',
                                         'balls': new_locked_balls})
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
        balls_added = 0
        for device in self._source_devices:
            balls_to_add = max(min(device.available_balls, balls - balls_added), 0)
            device.eject(balls=balls_to_add, target=self.source_playfield)
            balls_added += balls_to_add

        self.source_playfield.add_ball(balls=max(balls - balls_added, 0))
