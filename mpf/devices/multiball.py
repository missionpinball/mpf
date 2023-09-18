"""Contains the MultiBall device class."""
from mpf.core.enable_disable_mixin import EnableDisableMixin

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.mode_device import ModeDevice
from mpf.core.placeholder_manager import NativeTypeTemplate
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("shoot_again", "grace_period", "hurry_up", "balls_added_live", "balls_live_target")
class Multiball(EnableDisableMixin, SystemWideDevice, ModeDevice):

    """Multiball device for MPF."""

    config_section = 'multiballs'
    collection = 'multiballs'
    class_label = 'multiball'

    __slots__ = ["ball_locks", "source_playfield", "delay", "balls_added_live", "balls_live_target", "shoot_again",
                 "grace_period", "hurry_up"]

    def __init__(self, machine, name):
        """initialize multiball."""
        self.ball_locks = None
        self.source_playfield = None
        super().__init__(machine, name)

        self.delay = DelayManager(machine)
        self.balls_added_live = 0
        self.balls_live_target = 0
        self.shoot_again = False
        self.grace_period = False
        self.hurry_up = False

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return True

    def device_removed_from_mode(self, mode):
        """Disable and stop mb when mode stops."""
        super().device_removed_from_mode(mode)

        # also stop mb if shoot again is specified (aka the MB is currently running)
        if self.shoot_again:
            self.stop()

    async def _initialize(self):
        await super()._initialize()
        self.ball_locks = self.config['ball_locks']
        self.source_playfield = self.config['source_playfield']
        if isinstance(self.config['ball_count'], NativeTypeTemplate):
            ball_count = self.config['ball_count'].evaluate([])
        else:
            ball_count = None

        if self.config['ball_count_type'] == "total" and ball_count is not None and \
                ball_count <= 1:
            self.raise_config_error("ball_count should be at least 2 for a multiball to have an effect when "
                                    "ball_count_type is set to total.", 1)
        elif self.config['ball_count_type'] == "add" and ball_count is not None and \
                ball_count <= 0:
            self.raise_config_error("ball_count should be at least 1 for a multiball to have an effect when "
                                    "ball_count_type is set to add.", 2)

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
        ball_count = self.config['ball_count'].evaluate([])
        balls_to_replace = self.machine.game.balls_in_play if self.config['replace_balls_in_play'] else 0
        self.debug_log("Going to add an additional {} balls for replace_balls_in_play".format(balls_to_replace))

        if self.config['ball_count_type'] == "total":
            # policy: total balls
            if ball_count > self.machine.game.balls_in_play:
                self.balls_added_live = ball_count - self.machine.game.balls_in_play
                self.machine.game.balls_in_play = ball_count
            self.balls_live_target = ball_count
        else:
            # policy: add balls
            self.balls_added_live = ball_count
            self.machine.game.balls_in_play += self.balls_added_live
            self.balls_live_target = self.machine.game.balls_in_play

        self.balls_added_live += balls_to_replace

    @event_handler(10)
    def event_start(self, **kwargs):
        """Event handler for start event."""
        del kwargs
        self.start()

    def start(self):
        """Start multiball."""
        if not self.enabled:
            return

        if self.balls_live_target > 0:
            self.debug_log("Cannot start MB because %s are still in play",
                           self.balls_live_target)
            return

        self.shoot_again = True

        self._handle_balls_in_play_and_balls_live()
        self.debug_log("Starting multiball with %s balls (added %s)", self.balls_live_target, self.balls_added_live)

        balls_added = 0

        # eject balls from locks
        for device in self.ball_locks:
            balls_to_release = max(min(device.available_balls, self.balls_added_live - balls_added), 0)
            self.source_playfield.add_ball(balls=balls_to_release, source_device=device)
            balls_added += balls_to_release

        # request remaining balls
        if self.balls_added_live - balls_added > 0:
            self.source_playfield.add_ball(balls=self.balls_added_live - balls_added)

        shoot_again_ms = self.config['shoot_again'].evaluate([])
        if not shoot_again_ms:
            # No shoot again. Just stop multiball right away
            self.stop()
        else:
            # Enable shoot again
            self.machine.events.add_handler('ball_drain',
                                            self._ball_drain_shoot_again,
                                            priority=1000)
            self._timer_start()

        self.machine.events.post("multiball_" + self.name + "_started",
                                 balls=self.balls_live_target)
        '''event: multiball_(name)_started
        desc: The multiball called (name) has just started.
        args:
            balls: The number of balls in this multiball
        '''

    def _timer_start(self) -> None:
        """Start the timer.

        This is started when multiball starts if configured.
        """
        self.machine.events.post('ball_save_{}_timer_start'.format(self.name))
        '''event: ball_save_(name)_timer_start
        desc: The multiball ball save called (name) has just start its countdown timer.
        '''

        shoot_again_ms = self.config['shoot_again'].evaluate([])
        grace_period_ms = self.config['grace_period'].evaluate([])
        hurry_up_time_ms = self.config['hurry_up_time'].evaluate([])

        self._start_shoot_again(shoot_again_ms, grace_period_ms, hurry_up_time_ms)

    def _start_shoot_again(self, shoot_again_ms, grace_period_ms, hurry_up_time_ms):
        """Set callbacks for shoot again, grace period, and hurry up, if values above 0 are provided.

        This is started for both beginning multiball ball save and add a ball ball save
        """
        if shoot_again_ms > 0:
            self.debug_log('Starting ball save timer: %ss',
                           shoot_again_ms)
            self.delay.add(name='disable_shoot_again',
                           ms=(shoot_again_ms +
                               grace_period_ms),
                           callback=self.stop)
        if grace_period_ms > 0:
            self.grace_period = True
            self.delay.add(name='grace_period',
                           ms=shoot_again_ms,
                           callback=self._grace_period)
        if hurry_up_time_ms > 0:
            self.hurry_up = True
            self.delay.add(name='hurry_up',
                           ms=(shoot_again_ms -
                               hurry_up_time_ms),
                           callback=self._hurry_up)

    def _hurry_up(self) -> None:
        self.debug_log("Starting Hurry Up")

        self.hurry_up = False
        self.machine.events.post('multiball_{}_hurry_up'.format(self.name))
        '''event: multiball_(name)_hurry_up
        desc: The multiball ball save called (name) has just entered its hurry up mode.
        '''

    def _grace_period(self) -> None:
        self.debug_log("Starting Grace Period")

        self.grace_period = False
        self.machine.events.post('multiball_{}_grace_period'.format(self.name))
        '''event: multiball_(name)_grace_period
        desc: The multiball ball save called (name) has just entered its grace period
            time.
        '''

    def _ball_drain_shoot_again(self, balls, **kwargs):
        del kwargs

        balls_to_safe = self.balls_live_target - self.machine.game.balls_in_play + balls

        if balls_to_safe <= 0:
            return {'balls': balls}

        if balls_to_safe > balls:
            balls_to_safe = balls

        self.machine.events.post("multiball_" + self.name + "_shoot_again", balls=balls_to_safe)
        '''event: multiball_(name)_shoot_again
        desc: A ball has drained during the multiball called (name) while the
        ball save timer for that multiball was running, so a ball (or balls)
        will be saved and re-added into play.

        args:
            balls: The number of balls that are being saved.
        '''

        self.debug_log("Ball drained during MB. Requesting a new one")
        self.source_playfield.add_ball(balls=balls_to_safe)
        return {'balls': balls - balls_to_safe}

    def _ball_drain_count_balls(self, balls, **kwargs):
        del kwargs
        self.machine.events.post("multiball_{}_ball_lost".format(self.name))
        '''event: multiball_(name)_lost_ball
        desc: The multiball called (name) has lost a ball after ball save expired.
        '''

        if not self.machine.game or self.machine.game.balls_in_play - balls < 1:
            self.balls_added_live = 0
            self.balls_live_target = 0
            self.machine.events.remove_handler(self._ball_drain_count_balls)
            self.machine.events.post("multiball_{}_ended".format(self.name))
            '''event: multiball_(name)_ended
            desc: The multiball called (name) has just ended.
            '''
            self.debug_log("Ball drained. MB ended.")

    @event_handler(5)
    def event_stop(self, **kwargs):
        """Event handler for stop event."""
        del kwargs
        self.stop()

    def stop(self):
        """Stop shoot again."""
        self.debug_log("Stopping shoot again of multiball")
        self.shoot_again = False

        # disable shoot again
        self.machine.events.remove_handler(self._ball_drain_shoot_again)

        if self.grace_period:
            self.machine.events.remove_handler(self._grace_period)
            self._grace_period()
        if self.hurry_up:
            self.machine.events.remove_handler(self._hurry_up)
            self._hurry_up()
        self.machine.events.post("multiball_" + self.name + "_shoot_again_ended")
        '''event: multiball_(name)_shoot_again_ended
        desc: Shoot again for multiball (name) has ended.
        '''

        # add handler for ball_drain until self.balls_ejected are drained
        self.machine.events.remove_handler(self._ball_drain_count_balls)
        self.machine.events.add_handler('ball_drain', self._ball_drain_count_balls)

    @event_handler(8)
    def event_add_a_ball(self, **kwargs):
        """Event handler for add_a_ball event."""
        del kwargs
        self.add_a_ball()

    def add_a_ball(self):
        """Add a ball if multiball has started."""
        if self.balls_live_target > 0:
            self.debug_log("Adding a ball.")
            self.balls_live_target += 1
            self.balls_added_live += 1
            self.machine.game.balls_in_play += 1
            self.source_playfield.add_ball(balls=1)
            self._add_a_ball_timer_start()

    def _add_a_ball_timer_start(self) -> None:
        """Start the timer for add a ball ball save.

        This is started when multiball add a ball is triggered if configured,
        and the default timer is not still running.
        """
        if self.shoot_again:
            # if main ball save timer is running, don't run this timer
            return
        self.shoot_again = True

        shoot_again_ms = self.config['add_a_ball_shoot_again'].evaluate([])
        if not shoot_again_ms:
            # No shoot again. Just stop multiball right away
            self.stop()
            return
        # Enable shoot again
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_shoot_again,
                                        priority=1000)

        self.machine.events.post('ball_save_{}_add_a_ball_timer_start'.format(self.name))
        '''event: ball_save_(name)_add_a_ball_timer_start
        desc: The multiball add a ball ball save called (name) has just start its countdown timer.
        '''

        grace_period_ms = self.config['add_a_ball_grace_period'].evaluate([])
        hurry_up_time_ms = self.config['add_a_ball_hurry_up_time'].evaluate([])
        self._start_shoot_again(shoot_again_ms, grace_period_ms, hurry_up_time_ms)

    @event_handler(9)
    def event_start_or_add_a_ball(self, **kwargs):
        """Event handler for start_or_add_a_ball event."""
        del kwargs
        self.start_or_add_a_ball()

    def start_or_add_a_ball(self):
        """Start multiball or add a ball if multiball has started."""
        if self.balls_live_target > 0:
            self.add_a_ball()
        else:
            self.start()

    @event_handler(2)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset the multiball and disable it."""
        self.disable()
        self.shoot_again = False
        self.balls_added_live = 0
