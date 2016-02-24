""" Contains the MultiBall device class."""

from mpf.core.device import Device
from mpf.core.delays import DelayManager


class Multiball(Device):
    config_section = 'multiballs'
    collection = 'multiballs'
    class_label = 'multiball'

    def __init__(self, machine, name, config=None, validate=True):
        super().__init__(machine, name, config, validate=validate)

        self.delay = DelayManager(machine.delayRegistry)
        self.balls_ejected = 0
        self.enabled = False
        self.shoot_again = False

        # let ball devices initialise first
        self.machine.events.add_handler('init_phase_3',
                                        self._initialize)

    def device_added_to_mode(self, mode, player):
        del mode
        del player
        # initialize on mode
        self._initialize()

    def remove(self):
        # disable mb when mode ends
        self.disable()

        # also stop mb if no shoot again is specified
        self.stop()

    def _initialize(self):
        self.ball_locks = self.config['ball_locks']
        self.source_playfield = self.config['source_playfield']

        # start mb if no enable_events are specified
        if not self.config['enable_events']:
            self.enable()

    def start(self, **kwargs):
        del kwargs
        if not self.enabled:
            return

        if self.balls_ejected > 0:
            self.log.debug("Cannot start MB because %s are still in play",
                           self.balls_ejected)
            return

        self.shoot_again = True
        self.log.debug("Starting multiball with %s balls",
                       self.config['ball_count'])

        self.balls_ejected = self.config['ball_count'] - 1

        self.machine.game.add_balls_in_play(balls=self.balls_ejected)

        balls_added = 0

        # use lock_devices first
        for device in self.ball_locks:
            balls_added += device.release_balls(
                self.balls_ejected - balls_added)

            if self.balls_ejected - balls_added <= 0:
                break

        # request remaining balls
        if self.balls_ejected - balls_added > 0:
            self.source_playfield.add_ball(
                balls=self.balls_ejected - balls_added)

        if not self.config['shoot_again']:
            # No shoot again. Just stop multiball right away
            self.stop()
        else:
            # Enable shoot again
            self.machine.events.add_handler('ball_drain',
                                            self._ball_drain_shoot_again,
                                            priority=1000)
            # Register stop handler
            if self.config['shoot_again'] > 0:
                self.delay.add(name='disable_shoot_again',
                               ms=self.config['shoot_again'],
                               callback=self.stop)

        self.machine.events.post("multiball_" + self.name + "_started",
                                 balls=self.config['ball_count'])

    def _ball_drain_shoot_again(self, balls, **kwargs):
        del kwargs
        if balls <= 0:
            return {'balls': balls}

        self.machine.events.post("multiball_" + self.name + "_shoot_again",
                                 balls=balls)

        self.log.debug("Ball drained during MB. Requesting a new one")
        self.source_playfield.add_ball(balls=balls)
        return {'balls': 0}

    def _ball_drain_count_balls(self, balls, **kwargs):
        if "mb_claimed" in kwargs:
            claimed = kwargs['mb_claimed']
        else:
            claimed = 0

        # balls available to claim
        available_balls = balls - claimed

        if available_balls >= self.balls_ejected:
            claimed = self.balls_ejected
            self.balls_ejected = 0
            self.machine.events.remove_handler(self._ball_drain_count_balls)
            self.machine.events.post("multiball_" + self.name + "_ended")
            self.log.debug("Ball drained. MB ended.")
        else:
            self.balls_ejected -= available_balls
            self.log.debug("Ball drained. %s balls remain until MB ends",
                           self.balls_ejected)
            claimed = available_balls

        return {'balls': balls, 'mb_claimed': claimed}

    def stop(self, **kwargs):
        del kwargs
        self.log.debug("Stopping shoot again of multiball")
        self.shoot_again = False

        # disable shoot again
        self.machine.events.remove_handler(self._ball_drain_shoot_again)

        # add handler for ball_drain until self.balls_ejected are drained
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_count_balls)

    def enable(self, **kwargs):
        """ Enables the multiball. If the multiball is not enabled, it cannot
        start.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Enabling...")
        self.enabled = True

    def disable(self, **kwargs):
        """ Disabless the multiball. If the multiball is not enabled, it cannot
        start. Will not stop a running multiball.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Disabling...")
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the multiball and disables it.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.enabled = False
        self.shoot_again = False
        self.balls_ejected = 0
