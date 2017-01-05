"""Contains the BallLock device class."""

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode_device import ModeDevice


@DeviceMonitor("enabled")
class MultiballLock(ModeDevice):

    """Ball lock device which locks balls for a multiball."""

    config_section = 'multiball_locks'
    collection = 'multiball_locks'
    class_label = 'multiball_lock'

    def __init__(self, machine, name):
        """Initialise ball lock."""
        self.lock_devices = []
        self.source_playfield = None

        # initialise variables
        self.enabled = False
        self.initialised = False    # remove when #715 is fixed

        super().__init__(machine, name)

        self.machine.events.add_handler("player_turn_starting", self._player_turn_starting)

    def _add_balls_in_play(self, number):
        self.machine.game.balls_in_play += number

    def device_removed_from_mode(self, mode):
        """Disable ball lock when mode ends."""
        del mode
        self.disable()

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return False

    def _initialize(self):
        # load lock_devices
        super()._initialize()

        # we only need to initialise once
        if self.initialised:
            return

        self.lock_devices = []
        for device in self.config['lock_devices']:
            self.lock_devices.append(device)

        self.source_playfield = self.config['source_playfield']
        self.initialised = True

    def enable(self, **kwargs):
        """Enable the lock.

        If the lock is not enabled, no balls will be locked.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Enabling...")
        if not self.enabled:
            self._register_handlers()
        self.enabled = True

    def _player_turn_starting(self, queue, **kwargs):
        del kwargs
        if not self.initialised:
            return

        # check if the lock is physically full and not virtually full and release balls in that case
        if self._physically_remaining_space <= 0 and not self.is_virtually_full:
            self.log.info("Will release a ball because the lock is phyiscally full but not virtually for the current " +
                          "player.")
            # TODO: eject to next playfield
            self.lock_devices[0].eject()
            queue.wait()
            self.machine.events.add_handler("ball_drain", self._wait_for_drain, queue=queue)

    def _wait_for_drain(self, queue, balls, **kwargs):
        del kwargs
        if balls <= 0:
            return {'balls': balls}

        self.log.debug("Ball of lock drained.")

        queue.clear()

        self.machine.events.remove_handler_by_event('ball_drain', self._wait_for_drain)

        return {'balls': balls - 1}

    def disable(self, **kwargs):
        """Disable the lock.

        If the lock is not enabled, no balls will be locked.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Disabling...")
        self._unregister_handlers()
        self.enabled = False

    def reset_all_counts(self, **kwargs):
        """Reset the locked balls for all players."""
        del kwargs
        for player in self.machine.game.player_list:
            player['{}_locked_balls'.format(self.name)] = 0

    def reset_count_for_current_player(self, **kwargs):
        """Reset the locked balls for the current player."""
        del kwargs
        self.machine.game.player['{}_locked_balls'.format(self.name)] = 0

    @property
    def locked_balls(self):
        """Return the number of locked balls for the current player."""
        return self.machine.game.player['{}_locked_balls'.format(self.name)]

    @locked_balls.setter
    def locked_balls(self, value):
        """Set the number of locked balls for the current player."""
        self.machine.game.player['{}_locked_balls'.format(self.name)] = value

    def _register_handlers(self):
        # register on ball_enter of lock_devices
        for device in self.lock_devices:
            self.machine.events.add_handler(
                'balldevice_' + device.name + '_ball_enter',
                self._lock_ball, device=device)

    def _unregister_handlers(self):
        # unregister ball_enter handlers
        self.machine.events.remove_handler(self._lock_ball)

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

    def _lock_ball(self, unclaimed_balls, **kwargs):
        """Callback for _ball_enter event of lock_devices."""
        del kwargs
        # if full do not take any balls
        if self.is_virtually_full:
            self.log.debug("Cannot lock balls. Lock is full.")
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
            self.machine.events.post('multiball_lock_' + self.name + '_locked_ball',
                                     total_balls_locked=self.locked_balls)
            '''event: multiball_lock_(name)_locked_ball
            desc: The multiball lock device (name) has just locked one additional ball.

            args:
                total_balls_locked: The current total number of balls this device
                    has locked.
            '''

        # only keep ball if any player could use it
        if self._max_balls_locked_by_any_player <= self._physically_locked_balls:
            balls_to_lock_physically = 0

        # do not lock if the lock would be phyiscally full but not virtually
        if not self.is_virtually_full and self._physically_remaining_space <= 1:
            balls_to_lock_physically = 0

        # check if we are full now and post event if yes
        if self.is_virtually_full:
            self.machine.events.post('multiball_lock_' + self.name + '_full',
                                     balls=self.locked_balls)
        '''event: multiball_lock_(name)_full
        desc: The multiball lock device (name) is now full.
        args:
            balls: The number of balls currently locked in this device.
        '''

        # schedule eject of new balls for all physically locked balls
        self._request_new_balls(balls_to_lock_physically)

        self.log.debug("Locked %s balls virtually and %s balls physically", balls_to_lock, balls_to_lock_physically)

        return {'unclaimed_balls': unclaimed_balls - balls_to_lock_physically}

    def _request_new_balls(self, balls):
        """Request new ball to playfield."""
        self.source_playfield.add_ball(balls=balls)
