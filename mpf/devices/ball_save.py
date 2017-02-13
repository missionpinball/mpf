"""Device that implements a ball save."""

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("saves_remaining", "enabled", "timer_started")
class BallSave(SystemWideDevice, ModeDevice):

    """Ball save device which will give back the ball within a certain time."""

    config_section = 'ball_saves'
    collection = 'ball_saves'
    class_label = 'ball_save'

    def __init__(self, machine, name):
        """Initialise ball save."""
        self.unlimited_saves = None
        self.source_playfield = None
        super().__init__(machine, name)

        self.delay = DelayManager(machine.delayRegistry)
        self.enabled = False
        self.timer_started = False
        self.saves_remaining = 0
        self.early_saved = 0

    def _initialize(self):
        self.unlimited_saves = self.config['balls_to_save'] == -1
        self.source_playfield = self.config['source_playfield']

        # todo change the delays to timers so we can add pause and extension
        # events, but that will require moving timers out of mode conde

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return True

    def validate_and_parse_config(self, config: dict, is_mode_config: bool):
        """Make sure timer_start_events are not in enable_events."""
        config = super().validate_and_parse_config(config, is_mode_config)

        for event in config['timer_start_events']:
            if event in config['enable_events']:
                raise AssertionError("{}: event {} in timer_start_events will not work because it is also in "
                                     "enable_events. Omit it!".format(event, str(self)))

        return config

    def enable(self, **kwargs):
        """Enable ball save."""
        del kwargs
        if self.enabled:
            return

        self.saves_remaining = self.config['balls_to_save']
        self.early_saved = 0
        self.enabled = True
        self.log.debug("Enabling. Auto launch: %s, Balls to save: %s",
                       self.config['auto_launch'],
                       self.config['balls_to_save'])

        # Enable shoot again
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_while_active,
                                        priority=1000)

        if (self.config['active_time'] > 0 and
                not self.config['timer_start_events']):
            self.timer_start()

        self.machine.events.post('ball_save_{}_enabled'.format(self.name))
        '''event: ball_save_(name)_enabled
        desc: The ball save called (name) has just been enabled.
        '''

    def disable(self, **kwargs):
        """Disable ball save."""
        del kwargs
        if not self.enabled:
            return

        self.enabled = False
        self.timer_started = False
        self.log.debug("Disabling...")
        self.machine.events.remove_handler(self._ball_drain_while_active)
        self.delay.remove('disable')
        self.delay.remove('hurry_up')
        self.delay.remove('grace_period')

        self.machine.events.post('ball_save_{}_disabled'.format(self.name))
        '''event: ball_save_(name)_disabled
        desc: The ball save called (name) has just been disabled.
        '''

    def timer_start(self, **kwargs):
        """Start the timer.

        This is usually called after the ball was ejected while the ball save may have been enabled earlier.
        """
        del kwargs
        if self.timer_started or not self.enabled:
            return

        self.timer_started = True

        self.machine.events.post('ball_save_{}_timer_start'.format(self.name))
        '''event: ball_save_(name)_timer_start
        desc: The ball save called (name) has just start its countdown timer.
        '''

        if self.config['active_time'] > 0:
            if self.debug:
                self.log.debug('Starting ball save timer: %ss',
                               self.config['active_time'] / 1000.0)

            self.delay.add(name='disable',
                           ms=(self.config['active_time'] +
                               self.config['grace_period']),
                           callback=self.disable)
            self.delay.add(name='grace_period',
                           ms=self.config['active_time'],
                           callback=self._grace_period)
            self.delay.add(name='hurry_up',
                           ms=(self.config['active_time'] -
                               self.config['hurry_up_time']),
                           callback=self._hurry_up)

    def _hurry_up(self):
        if self.debug:
            self.log.debug("Starting Hurry Up")

        self.machine.events.post('ball_save_{}_hurry_up'.format(self.name))
        '''event: ball_save_(name)_hurry_up
        desc: The ball save called (name) has just entered its hurry up mode.
        '''

    def _grace_period(self):
        if self.debug:
            self.log.debug("Starting Grace Period")

        self.machine.events.post('ball_save_{}_grace_period'.format(self.name))
        '''event: ball_save_(name)_grace_period
        desc: The ball save called (name) has just entered its grace period
            time.
        '''

    def _get_number_of_balls_to_save(self, available_balls):
        no_balls_in_play = False

        try:
            if not self.machine.game.balls_in_play:
                no_balls_in_play = True

            if self.config['only_last_ball'] and self.machine.game.balls_in_play > 1:
                self.log.debug("Will only save last ball but %s are in play.", self.machine.game.balls_in_play)
                return 0
        except AttributeError:
            no_balls_in_play = True

        if no_balls_in_play:
            self.log.debug("Received request to save ball, but no balls are in"
                           " play. Discarding request.")
            return 0

        balls_to_save = available_balls

        if self.config['only_last_ball'] and balls_to_save > 1:
            balls_to_save = 1

        if balls_to_save > self.machine.game.balls_in_play:
            balls_to_save = self.machine.game.balls_in_play

        if balls_to_save > self.saves_remaining and not self.unlimited_saves:
            balls_to_save = self.saves_remaining

        return balls_to_save

    def _reduce_remaining_saves_and_disable_if_zero(self, balls_to_save):
        if not self.unlimited_saves:
            self.saves_remaining -= balls_to_save
            if self.debug:
                self.log.debug("Saves remaining: %s", self.saves_remaining)
        elif self.debug:
            self.log.debug("Unlimited saves remaining")

        if self.saves_remaining <= 0 and not self.unlimited_saves:
            if self.debug:
                self.log.debug("Disabling since there are no saves remaining")
            self.disable()

    def _ball_drain_while_active(self, balls, **kwargs):
        del kwargs
        if balls <= 0:
            return

        balls_to_save = self._get_number_of_balls_to_save(balls)

        self.log.debug("Ball(s) drained while active. Requesting new one(s). "
                       "Autolaunch: %s", self.config['auto_launch'])

        self.machine.events.post('ball_save_{}_saving_ball'.format(self.name),
                                 balls=balls_to_save, early_save=False)
        '''event: ball_save_(name)_saving_ball
        desc: The ball save called (name) has just saved one (or more) balls.

        args:
            balls: The number of balls this ball saver is saving.
            early_save: True if this is an early ball save.
        '''

        self._schedule_balls(balls_to_save)

        self._reduce_remaining_saves_and_disable_if_zero(balls_to_save)

        return {'balls': balls - balls_to_save}

    def early_ball_save(self, **kwargs):
        """Perform early ball save if enabled."""
        del kwargs
        if not self.enabled:
            return

        if not self._get_number_of_balls_to_save(1):
            return

        if self.early_saved > 0:
            self.log.debug("Already performed an early ball save. Ball needs to drain first.")
            return

        self.machine.events.post('ball_save_{}_saving_ball'.format(self.name),
                                 balls=1, early_save=True)
        # doc block above

        self.log.debug("Performing early ball save.")
        self.early_saved += 1
        self._schedule_balls(1)
        self.machine.events.add_handler('ball_drain',
                                        self._early_ball_save_drain_handler,
                                        priority=1001)

        self._reduce_remaining_saves_and_disable_if_zero(1)

    def _early_ball_save_drain_handler(self, balls, **kwargs):
        del kwargs
        if self.early_saved and balls > 0:
            balls -= 1
            self.early_saved -= 1
            self.log.debug("Early saved ball drained.")
            self.machine.events.remove_handler(self._early_ball_save_drain_handler)
            return {'balls': balls}

    def _schedule_balls(self, balls_to_save):
        if self.config['eject_delay']:
            self.delay.add(self.config['eject_delay'], self._add_balls, balls_to_save=balls_to_save)
        else:
            self._add_balls(balls_to_save)

    def _add_balls(self, balls_to_save, **kwargs):
        del kwargs
        self.source_playfield.add_ball(balls=balls_to_save,
                                       player_controlled=self.config['auto_launch'] ^ 1)

    def device_removed_from_mode(self, mode):
        """Disable ball save when mode ends."""
        del mode
        if self.debug:
            self.log.debug("Removing...")

        self.disable()
