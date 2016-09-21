"""Contains the MultiBall device class."""

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("enabled", "shoot_again", "balls_added_live", "balls_live_target")
class Multiball(SystemWideDevice, ModeDevice):

    """Multiball device for MPF."""

    config_section = 'multiballs'
    collection = 'multiballs'
    class_label = 'multiball'

    def __init__(self, machine, name):
        """Initialise multiball."""
        self.ball_locks = None
        self.source_playfield = None
        super().__init__(machine, name)

        self.delay = DelayManager(machine.delayRegistry)
        self.balls_added_live = 0
        self.balls_live_target = 0
        self.enabled = False
        self.shoot_again = False

    def device_removed_from_mode(self, mode):
        """Disable and stop mb when mode stops."""
        del mode
        # disable mb when mode ends
        self.disable()

        # also stop mb if no shoot again is specified
        self.stop()

    def _initialize(self):
        self.ball_locks = self.config['ball_locks']
        self.source_playfield = self.config['source_playfield']

    @classmethod
    def prepare_config(cls, config, is_mode_config):
        """Add default enable_events and disable_events outside mode."""
        if not is_mode_config:
            if 'enable_events' not in config:
                config['enable_events'] = 'ball_started'
            if 'disable_events' not in config:
                config['disable_events'] = 'ball_will_end'
        return super().prepare_config(config, is_mode_config)

    def _handle_balls_in_play_and_balls_live(self):
        if self.config['ball_count_type'] == "total":
            # policy: total balls
            if self.config['ball_count'] > self.machine.game.balls_in_play:
                self.balls_added_live = self.config['ball_count'] - self.machine.game.balls_in_play
                self.machine.game.balls_in_play = self.config['ball_count']
            self.balls_live_target = self.config['ball_count']
        else:
            # policy: add balls
            self.balls_added_live = self.config['ball_count']
            self.machine.game.balls_in_play += self.balls_added_live
            self.balls_live_target = self.machine.game.balls_in_play

    def start(self, **kwargs):
        """Start multiball."""
        del kwargs
        if not self.enabled:
            return

        if self.balls_live_target > 0:
            self.log.debug("Cannot start MB because %s are still in play",
                           self.balls_added_live)
            return

        self.shoot_again = True
        self.log.debug("Starting multiball with %s balls",
                       self.config['ball_count'])

        self._handle_balls_in_play_and_balls_live()

        balls_added = 0

        # always eject all locks
        for device in self.ball_locks:
            balls_added += device.release_all_balls()

        # increase balls_in_play if necessary
        if balls_added > self.balls_added_live:
            self.log.info("Added %s excess balls found in locks.", balls_added - self.balls_added_live)
            self.machine.game.balls_in_play += balls_added - self.balls_added_live
            self.balls_added_live = balls_added

        # request remaining balls
        if self.balls_added_live - balls_added > 0:
            self.source_playfield.add_ball(balls=self.balls_added_live - balls_added)

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
        '''event: multiball_(name)_started
        desc: The multiball called (name) has just started.
        args:
            balls: The number of balls in this multiball
        '''

    def _ball_drain_shoot_again(self, balls, **kwargs):
        del kwargs

        balls_to_safe = self.balls_live_target - self.machine.game.balls_in_play + balls

        if balls_to_safe <= 0:
            return {'balls': balls}

        self.machine.events.post("multiball_" + self.name + "_shoot_again", balls=balls_to_safe)
        '''event: multiball_(name)_shoot_again
        desc: A ball has drained during the multiball called (name) while the
        ball save timer for that multiball was running, so a ball (or balls)
        will be saved and re-added into play.

        args:
            balls: The number of balls that are being saved.
        '''

        self.log.debug("Ball drained during MB. Requesting a new one")
        self.source_playfield.add_ball(balls=balls_to_safe)
        return {'balls': balls - balls_to_safe}

    def _ball_drain_count_balls(self, balls, **kwargs):
        del kwargs
        self.machine.events.post("multiball_{}_ball_lost".format(self.name))
        '''event: multiball_(name)_lost_ball
        desc: The multiball called (name) has lost a ball after ball save expired.
        '''

        if self.machine.game.balls_in_play - balls < 1:
            self.balls_added_live = 0
            self.balls_live_target = 0
            self.machine.events.remove_handler(self._ball_drain_count_balls)
            self.machine.events.post("multiball_{}_ended".format(self.name))
            '''event: multiball_(name)_ended
            desc: The multiball called (name) has just ended.
            '''
            self.log.debug("Ball drained. MB ended.")

    def stop(self, **kwargs):
        """Stop shoot again."""
        del kwargs
        self.log.debug("Stopping shoot again of multiball")
        self.shoot_again = False

        # disable shoot again
        self.machine.events.remove_handler(self._ball_drain_shoot_again)

        # add handler for ball_drain until self.balls_ejected are drained
        self.machine.events.add_handler('ball_drain', self._ball_drain_count_balls)

    def enable(self, **kwargs):
        """Enable the multiball.

        If the multiball is not enabled, it cannot start.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Enabling...")
        self.enabled = True

    def disable(self, **kwargs):
        """Disable the multiball.

        If the multiball is not enabled, it cannot start. Will not stop a running multiball.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.log.debug("Disabling...")
        self.enabled = False

    def reset(self, **kwargs):
        """Reset the multiball and disable it.

        Args:
            **kwargs: unused
        """
        del kwargs
        self.enabled = False
        self.shoot_again = False
        self.balls_added_live = 0
