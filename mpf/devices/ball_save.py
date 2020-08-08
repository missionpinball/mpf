"""Device that implements a ball save."""
from typing import Optional

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.playfield import Playfield     # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor("saves_remaining", "enabled", "timer_started", "state")
class BallSave(SystemWideDevice, ModeDevice):

    """Ball save device which will give back the ball within a certain time."""

    config_section = 'ball_saves'
    collection = 'ball_saves'
    class_label = 'ball_save'

    __slots__ = ["active_time", "unlimited_saves", "source_playfield", "delay", "enabled", "timer_started",
                 "saves_remaining", "early_saved", "state", "_scheduled_balls"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialise ball save."""
        self.unlimited_saves = None         # type: Optional[bool]
        self.source_playfield = None        # type: Optional[Playfield]
        super().__init__(machine, name)

        self.delay = DelayManager(machine)
        self.enabled = False
        self.timer_started = False
        self.saves_remaining = 0
        self.early_saved = 0
        self.state = 'disabled'
        self._scheduled_balls = 0
        self.active_time = 0

    async def _initialize(self) -> None:
        await super()._initialize()
        self.unlimited_saves = self.config['balls_to_save'] == -1
        self.source_playfield = self.config['source_playfield']

    @property
    def can_exist_outside_of_game(self) -> bool:
        """Return true if this device can exist outside of a game."""
        return True

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Make sure timer_start_events are not in enable_events."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)

        for event in config['timer_start_events']:
            if event in config['enable_events']:
                raise AssertionError("{}: event {} in timer_start_events will not work because it is also in "
                                     "enable_events. Omit it!".format(event, str(self)))

        if config['delayed_eject_events'] and config['eject_delay']:
            raise AssertionError("cannot use delayed_eject_events and eject_delay at the same time.")

        return config

    def enable(self) -> None:
        """Enable ball save."""
        super().enable()
        if self.enabled:
            return

        self.saves_remaining = self.config['balls_to_save']
        self.early_saved = 0
        self.enabled = True
        self.state = 'enabled'
        self.active_time = self.config['active_time'].evaluate([])
        self.debug_log("Enabling. Auto launch: {}, Balls to save: {}, Active time: {}s".format(
                       self.config['auto_launch'],
                       self.config['balls_to_save'],
                       self.active_time))

        # Enable shoot again
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_while_active,
                                        priority=1000)

        if (self.active_time > 0 and
                not self.config['timer_start_events']):
            self.timer_start()

        self.machine.events.post('ball_save_{}_enabled'.format(self.name))
        '''event: ball_save_(name)_enabled
        desc: The ball save called (name) has just been enabled.
        '''

    @event_handler(1)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self) -> None:
        """Disable ball save."""
        if not self.enabled:
            return

        self.enabled = False
        self.state = 'disabled'
        self.timer_started = False
        self.debug_log("Disabling...")
        self.machine.events.remove_handler(self._ball_drain_while_active)
        self.delay.remove('disable')
        self.delay.remove('hurry_up')
        self.delay.remove('grace_period')

        self.machine.events.post('ball_save_{}_disabled'.format(self.name))
        '''event: ball_save_(name)_disabled
        desc: The ball save called (name) has just been disabled.
        '''

    @event_handler(9)
    def event_timer_start(self, **kwargs):
        """Event handler for timer start event."""
        del kwargs
        self.timer_start()

    def timer_start(self) -> None:
        """Start the timer.

        This is usually called after the ball was ejected while the ball save may have been enabled earlier.
        """
        if self.timer_started or not self.enabled:
            return

        self.timer_started = True

        self.machine.events.post('ball_save_{}_timer_start'.format(self.name))
        '''event: ball_save_(name)_timer_start
        desc: The ball save called (name) has just start its countdown timer.
        '''

        if self.active_time > 0:
            self.debug_log('Starting ball save timer: %ss',
                           self.active_time)
            active_time_ms = self.active_time * 1000
            self.delay.add(name='disable',
                           ms=(active_time_ms +
                               self.config['grace_period']),
                           callback=self.disable)
            self.delay.add(name='grace_period',
                           ms=active_time_ms,
                           callback=self._grace_period)
            self.delay.add(name='hurry_up',
                           ms=(active_time_ms -
                               self.config['hurry_up_time']),
                           callback=self._hurry_up)

    def _hurry_up(self) -> None:
        self.debug_log("Starting Hurry Up")

        self.state = 'hurry_up'

        self.machine.events.post('ball_save_{}_hurry_up'.format(self.name))
        '''event: ball_save_(name)_hurry_up
        desc: The ball save called (name) has just entered its hurry up mode.
        '''

    def _grace_period(self) -> None:
        self.debug_log("Starting Grace Period")

        self.state = 'grace_period'

        self.machine.events.post('ball_save_{}_grace_period'.format(self.name))
        '''event: ball_save_(name)_grace_period
        desc: The ball save called (name) has just entered its grace period
            time.
        '''

    def _get_number_of_balls_to_save(self, available_balls: int) -> int:
        if self.machine.game and self.machine.game.balls_in_play > 0:
            if self.config['only_last_ball'] and self.machine.game.balls_in_play > 1:
                self.debug_log("Will only save last ball but %s are in play.", self.machine.game.balls_in_play)
                return 0
        else:
            self.debug_log("Received request to save ball, but no balls are in"
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

    def _reduce_remaining_saves_and_disable_if_zero(self, balls_to_save: int) -> None:
        if not self.unlimited_saves:
            self.saves_remaining -= balls_to_save
            self.debug_log("Saves remaining: %s", self.saves_remaining)
        else:
            self.debug_log("Unlimited saves remaining")

        if self.saves_remaining <= 0 and not self.unlimited_saves:
            self.debug_log("Disabling since there are no saves remaining")
            self.disable()

    def _ball_drain_while_active(self, balls: int, **kwargs) -> Optional[dict]:
        del kwargs
        if balls <= 0:
            return {}

        balls_to_save = self._get_number_of_balls_to_save(balls)

        self.debug_log("Ball(s) drained while active. Requesting new one(s). "
                       "Auto launch: %s", self.config['auto_launch'])

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

    @event_handler(8)
    def event_early_ball_save(self, **kwargs):
        """Event handler for early_ball_save event."""
        del kwargs
        self.early_ball_save()

    def early_ball_save(self) -> None:
        """Perform early ball save if enabled."""
        if not self.enabled:
            return

        if not self._get_number_of_balls_to_save(1):
            return

        if self.early_saved > 0:
            self.debug_log("Already performed an early ball save. Ball needs to drain first.")
            return

        self.machine.events.post('ball_save_{}_saving_ball'.format(self.name),
                                 balls=1, early_save=True)
        # doc block above

        self.debug_log("Performing early ball save.")
        self.early_saved += 1
        self._schedule_balls(1)
        self.machine.events.add_handler('ball_drain',
                                        self._early_ball_save_drain_handler,
                                        priority=1001)

        self._reduce_remaining_saves_and_disable_if_zero(1)

    def _early_ball_save_drain_handler(self, balls: int, **kwargs) -> dict:
        del kwargs
        if self.early_saved and balls > 0:
            balls -= 1
            self.early_saved -= 1
            self.debug_log("Early saved ball drained.")
            self.machine.events.remove_handler(self._early_ball_save_drain_handler)
            return {'balls': balls}

        return {}

    def _schedule_balls(self, balls_to_save: int) -> None:
        if self.config['eject_delay']:
            # schedule after delay. to add some drama
            self.delay.add(self.config['eject_delay'], self._add_balls, balls_to_save=balls_to_save)
        elif self.config['delayed_eject_events']:
            # unlimited delay. wait for event
            self._scheduled_balls += balls_to_save
        else:
            # default: no delay. just eject balls right now
            self._add_balls(balls_to_save)

    @event_handler(4)
    def event_delayed_eject(self, **kwargs):
        """Event handler for delayed_eject event."""
        del kwargs
        self.delayed_eject()

    def delayed_eject(self):
        """Trigger eject of all scheduled balls."""
        self._add_balls(self._scheduled_balls)
        self._scheduled_balls = 0

    def _add_balls(self, balls_to_save, **kwargs):
        del kwargs
        self.source_playfield.add_ball(balls=balls_to_save,
                                       player_controlled=self.config['auto_launch'] ^ 1)

    def device_removed_from_mode(self, mode: Mode) -> None:
        """Disable ball save when mode ends."""
        super().device_removed_from_mode(mode)
        self.debug_log("Removing...")

        self.disable()

        if self.config['delayed_eject_events']:
            self.debug_log("Triggering delayed eject because mode ended.")
            self.delayed_eject()
