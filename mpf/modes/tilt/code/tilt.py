"""Contains the Tilt mode code."""
from typing import Set, Any

from mpf.core.events import EventHandlerKey
from mpf.core.events import QueuedEvent
from mpf.core.machine import MachineController
from mpf.core.mode import Mode


class Tilt(Mode):

    """A mode which handles a tilt in a pinball machine.

    Note that this mode is always running (even during attract mode) since the
    machine needs to watch for slam tilts at all times.
    """

    __slots__ = ["_balls_to_collect", "_last_warning", "ball_ending_tilted_queue", "tilt_event_handlers",
                 "last_tilt_warning_switch", "tilt_config", "_settle_time", "_warnings_to_tilt", "_multiple_hit_window"]

    def __init__(self, machine: MachineController, config: dict, name: str, path) -> None:
        """Create mode."""
        self._balls_to_collect = None   # type: int
        self._last_warning = None       # type: int
        self.ball_ending_tilted_queue = None    # type: QueuedEvent
        self.tilt_event_handlers = None         # type: Set[EventHandlerKey]
        self.last_tilt_warning_switch = None    # type: int
        self.tilt_config = None                 # type: Any
        self._settle_time = None
        self._warnings_to_tilt = None
        self._multiple_hit_window = None
        super().__init__(machine, config, name, path)

    def mode_init(self):
        """Initialise mode."""
        self._balls_to_collect = 0
        self._last_warning = None
        self.ball_ending_tilted_queue = None
        self.tilt_event_handlers = set()
        self.last_tilt_warning_switch = 0

        self.tilt_config = self.machine.config_validator.validate_config(
            config_spec='tilt',
            source=self.config.get('tilt', {}),
            section_name='tilt')

    def mode_start(self, **kwargs):
        """Start mode."""
        self._register_switch_handlers()

        for event in self.tilt_config['reset_warnings_events']:
            self.add_mode_event_handler(event, self.reset_warnings)

        for event in self.tilt_config['tilt_events']:
            self.add_mode_event_handler(event, self.tilt)

        for event in self.tilt_config['tilt_warning_events']:
            self.add_mode_event_handler(event, self.tilt_warning)

        for event in self.tilt_config['tilt_slam_tilt_events']:
            self.add_mode_event_handler(event, self.slam_tilt)

        self._settle_time = self.tilt_config['settle_time'].evaluate([])
        self._warnings_to_tilt = self.tilt_config['warnings_to_tilt'].evaluate([])
        self._multiple_hit_window = self.tilt_config['multiple_hit_window'].evaluate([])

    def mode_stop(self, **kwargs):
        """Stop mode."""
        self._remove_switch_handlers()

    def _register_switch_handlers(self):
        for switch in self.machine.switches.items_tagged(
                self.tilt_config['tilt_warning_switch_tag']):
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self._tilt_warning_switch_handler)

        for switch in self.machine.switches.items_tagged(
                self.tilt_config['tilt_switch_tag']):
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self.tilt)

        for switch in self.machine.switches.items_tagged(
                self.tilt_config['slam_tilt_switch_tag']):
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self.slam_tilt)

    def _remove_switch_handlers(self):
        for switch in self.machine.switches.items_tagged(
                self.tilt_config['tilt_warning_switch_tag']):
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self._tilt_warning_switch_handler)
        for switch in self.machine.switches.items_tagged(
                self.tilt_config['tilt_switch_tag']):
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self.tilt)
        for switch in self.machine.switches.items_tagged(
                self.tilt_config['slam_tilt_switch_tag']):
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self.slam_tilt)

    # ignore false positives about self.player
    # pylint: disable-msg=unsubscriptable-object,unsupported-assignment-operation
    def tilt_warning(self, **kwargs):
        """Process a tilt warning.

        If the number of warnings is the number to cause a tilt, a tilt will be
        processed.
        """
        del kwargs
        self.last_tilt_warning_switch = self.machine.clock.get_time()

        if not self.machine.game or not self.machine.game.player or self.machine.game.ending:
            return

        self.info_log("Tilt Warning")

        self._last_warning = self.machine.clock.get_time()
        self.machine.game.player[self.tilt_config['tilt_warnings_player_var']] += 1

        warnings = self.machine.game.player[self.tilt_config['tilt_warnings_player_var']]

        warnings_to_tilt = self._warnings_to_tilt
        if warnings >= warnings_to_tilt:
            self.tilt()
        else:
            self.machine.events.post(
                'tilt_warning',
                warnings=warnings,
                warnings_remaining=warnings_to_tilt - warnings)
            '''event: tilt_warning
            desc: A tilt warning just happened.
            args:
            warnings: The total number of warnings so far.
            warnings_remaining: The remaining number of warnings until a tilt.
            '''
            self.machine.events.post('tilt_warning_{}'.format(warnings))
            '''event: tilt_warning_(number)
            desc: A tilt warning just happened. The number of this tilt
            warning is in the event name in the (number).'''

    def reset_warnings(self, **kwargs):
        """Reset the tilt warnings for the current player."""
        del kwargs
        if not self.machine.game or not self.machine.game.player or self.machine.game.ending:
            return

        try:
            self.machine.game.player[self.tilt_config['tilt_warnings_player_var']] = 0
        except AttributeError:
            pass

    def tilt(self, **kwargs):
        """Cause the ball to tilt.

        This will post an event called *tilt*, set the game mode's ``tilted``
        attribute to *True*, disable the flippers and autofire devices, end the
        current ball, and wait for all the balls to drain.
        """
        del kwargs
        if not self.machine.game or self.machine.game.tilted or self.machine.game.ending:
            return

        self.machine.game.tilted = True

        self._balls_to_collect = 0
        for device in self.machine.ball_devices.values():
            if device.is_playfield():
                self._balls_to_collect += device.available_balls

        self.info_log("Processing Tilt. Balls to collect: %s",
                      self._balls_to_collect)

        self.machine.events.post('tilt')
        '''event: tilt
        desc: The player has tilted.'''

        self.tilt_event_handlers.add(
            self.machine.events.add_handler('player_turn_ending', self._ball_ending_tilted))

        for device in self.machine.ball_devices.values():
            if 'drain' in device.tags:
                self.tilt_event_handlers.add(
                    self.machine.events.add_handler(
                        'balldevice_{}_ball_enter'.format(device.name),
                        self._tilted_ball_drain))

        self.machine.game.end_ball()

    def _tilted_ball_drain(self, new_balls, unclaimed_balls, device, **kwargs):
        del new_balls
        del device
        del kwargs

        self._balls_to_collect -= unclaimed_balls

        self.debug_log("Tilted ball drain. Balls to collect: %s",
                       self._balls_to_collect)

        if self._balls_to_collect <= 0:
            self._tilt_done()

    def _tilt_switch_handler(self):
        self.tilt()

    def _tilt_warning_switch_handler(self):
        if (not self._last_warning or
                (self._last_warning + (self._multiple_hit_window * 0.001) <=
                 self.machine.clock.get_time())):

            self.tilt_warning()

    def _ball_ending_tilted(self, queue, **kwargs):
        del kwargs
        self.ball_ending_tilted_queue = queue
        queue.wait()

        if not self._balls_to_collect:
            self._tilt_done()

    def _tilt_done(self):
        if self.tilt_settle_ms_remaining():
            self.delay.reset(ms=self.tilt_settle_ms_remaining(),
                             callback=self._tilt_done,
                             name='tilt')

        else:
            self.machine.game.tilted = False

            self.machine.events.post('tilt_clear')
            '''event: tilt_clear
            desc: Posted after a tilt, when the settling time has passed after
            the last tilt switch hit. This is used to hold the next ball
            start until the plumb bob has settled to prevent tilt throughs.
            '''

            if self.ball_ending_tilted_queue:
                self.ball_ending_tilted_queue.clear()
                self.ball_ending_tilted_queue = None

            self.machine.events.remove_handlers_by_keys(
                self.tilt_event_handlers)
            self.tilt_event_handlers = set()

    def tilt_settle_ms_remaining(self):
        """Return the amount of milliseconds remaining until the tilt settle time has cleared.

        Returns:
            Integer of the number of ms remaining until tilt settled is cleared.
        """
        if not self.last_tilt_warning_switch:
            return 0

        delta = (self._settle_time -
                 (self.machine.clock.get_time() -
                  self.last_tilt_warning_switch) * 1000)
        if delta > 0:
            return delta
        else:
            return 0

    def slam_tilt(self, **kwargs):
        """Process a slam tilt.

        This method posts the *slam_tilt* event and (if a game is active) sets
        the game mode's ``slam_tilted`` attribute to *True*.
        """
        del kwargs
        self.machine.events.post('slam_tilt')
        '''event: slam_tilt
        desc: A slam tilt has just occurred.'''
        if not self.machine.game:
            return

        self.machine.game.slam_tilted = True
        self.tilt()
