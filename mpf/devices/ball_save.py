"""Device that implements a ball save."""

from mpf.core.delays import DelayManager
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


class BallSave(SystemWideDevice, ModeDevice):
    config_section = 'ball_saves'
    collection = 'ball_saves'
    class_label = 'ball_save'

    def __init__(self, machine, name):
        super().__init__(machine, name)

        self.delay = DelayManager(machine.delayRegistry)
        self.enabled = False
        self.timer_started = False
        self.saves_remaining = 0

    def _initialize(self):
        self.unlimited_saves = self.config['balls_to_save'] == -1
        self.source_playfield = self.config['source_playfield']

        # todo change the delays to timers so we can add pause and extension
        # events, but that will require moving timers out of mode conde

    def enable(self, **kwargs):
        del kwargs
        if self.enabled:
            return

        self.saves_remaining = self.config['balls_to_save']
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
        '''event: ball_save_(name)_enabled:
        desc: The ball save called (name) has just been enabled.
        '''

    def disable(self, **kwargs):
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
        '''event: ball_save_(name)_disabled:
        desc: The ball save called (name) has just been disabled.
        '''

    def timer_start(self, **kwargs):
        del kwargs
        if self.timer_started or not self.enabled:
            return

        self.machine.events.post('ball_save_{}_timer_start'.format(self.name))
        '''event: ball_save_(name)_timer_start:
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
        '''event: ball_save_(name)_hurry_up:
        desc: The ball save called (name) has just entered its hurry up mode.
        '''

    def _grace_period(self):
        if self.debug:
            self.log.debug("Starting Grace Period")

        self.machine.events.post('ball_save_{}_grace_period'.format(self.name))
        '''event: ball_save_(name)_grace_period:
        desc: The ball save called (name) has just entered its grace period
            time.
        '''

    def _ball_drain_while_active(self, balls, **kwargs):
        del kwargs
        if balls <= 0:
            return {'balls': balls}

        no_balls_in_play = False

        try:
            if not self.machine.game.balls_in_play:
                no_balls_in_play = True
        except AttributeError:
            no_balls_in_play = True

        if no_balls_in_play:
            self.log.debug("Received request to save ball, but no balls are in"
                           " play. Discarding request.")
            return {'balls': balls}

        balls_to_save = balls

        if balls_to_save > self.machine.game.balls_in_play:
            balls_to_save = self.machine.game.balls_in_play

        if balls_to_save > self.saves_remaining and not self.unlimited_saves:
            balls_to_save = self.saves_remaining

        self.log.debug("Ball(s) drained while active. Requesting new one(s). "
                       "Autolaunch: %s", self.config['auto_launch'])

        self.machine.events.post('ball_save_{}_saving_ball'.format(self.name),
                                 balls=balls_to_save)
        '''event: ball_save_(name)_saving_ball:
        desc: The ball save called (name) has just saved one (or more) balls.

        args:
            balls: The number of balls this ball saver is saving.
        '''

        self.source_playfield.add_ball(balls=balls_to_save,
                                       player_controlled=self.config[
                                                             'auto_launch'] ^ 1)

        if not self.unlimited_saves:
            self.saves_remaining -= balls_to_save
            if self.debug:
                self.log.debug("Saves remaining: %s", self.saves_remaining)
        elif self.debug:
            self.log.debug("Unlimited Saves enabled")

        if self.saves_remaining <= 0 and not self.unlimited_saves:
            if self.debug:
                self.log.debug("Disabling since there are no saves remaining")
            self.disable()

        return {'balls': balls - balls_to_save}

    def device_removed_from_mode(self):
        if self.debug:
            self.log.debug("Removing...")

        self.disable()
