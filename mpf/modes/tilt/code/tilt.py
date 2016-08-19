"""Contains the Tilt mode code."""
from mpf.core.machine import MachineController
from mpf.core.mode import Mode


class Tilt(Mode):

    """A mode which handles a tilt in a pinball machine."""

    def __init__(self, machine: MachineController, config: dict, name: str, path):
        """Create mode."""
        self._balls_to_collect = None
        self._last_warning = None
        self.ball_ending_tilted_queue = None
        self.tilt_event_handlers = None
        self.last_tilt_warning_switch = None
        self.tilt_config = None
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
            source=self._get_merged_settings('tilt'),
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
    # pylint: disable-msg=unsubscriptable-object
    def tilt_warning(self):
        """Process a tilt warning.

         If the number of warnings is the number to
        cause a tilt, a tilt will be processed.
        """
        self.last_tilt_warning_switch = self.machine.clock.get_time()

        if not self.player:
            return

        self.log.debug("Tilt Warning")

        self._last_warning = self.machine.clock.get_time()
        self.player[self.tilt_config['tilt_warnings_player_var']] += 1

        warnings = self.player[self.tilt_config['tilt_warnings_player_var']]

        if warnings >= self.tilt_config['warnings_to_tilt']:
            self.tilt()
        else:
            self.machine.events.post(
                'tilt_warning',
                warnings=warnings,
                warnings_remaining=(self.tilt_config['warnings_to_tilt'] -
                                    warnings))
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
        try:
            self.player[self.tilt_config['tilt_warnings_player_var']] = 0
        except AttributeError:
            pass

    def tilt(self, **kwargs):
        """Cause the ball to tilt."""
        del kwargs
        if not self.machine.game:
            return

        self.machine.game.tilted = True

        self._balls_to_collect = 0
        for device in self.machine.ball_devices:
            if device.is_playfield():
                self._balls_to_collect += device.available_balls

        self.log.debug("Processing Tilt. Balls to collect: %s",
                       self._balls_to_collect)

        self.machine.game.tilted = True
        self.machine.events.post('tilt')
        '''event: tilt
        desc: The player has tilted.'''
        self._disable_autofires()
        self._disable_flippers()

        self.tilt_event_handlers.add(
            self.machine.events.add_handler('ball_ending',
                                            self._ball_ending_tilted))

        for device in self.machine.ball_devices:
            if 'drain' in device.tags:
                self.tilt_event_handlers.add(
                    self.machine.events.add_handler(
                        'balldevice_{}_ball_enter'.format(device.name),
                        self._tilted_ball_drain))

        self.machine.game.ball_ending()

    def _disable_flippers(self):
        for flipper in self.machine.flippers:
            flipper.disable()

    def _disable_autofires(self):
        for autofire in self.machine.autofires:
            autofire.disable()

    def _tilted_ball_drain(self, new_balls, unclaimed_balls, device, **kwargs):
        del new_balls
        del device
        del kwargs

        self._balls_to_collect -= unclaimed_balls

        self.log.debug("Tilted ball drain. Balls to collect: %s",
                       self._balls_to_collect)

        if self._balls_to_collect <= 0:
            self._tilt_done()

        return {'unclaimed_balls': 0}

    def _tilt_switch_handler(self):
        self.tilt()

    def _tilt_warning_switch_handler(self):
        if (not self._last_warning or
                (self._last_warning + (self.tilt_config['multiple_hit_window'] * 0.001) <=
                 self.machine.clock.get_time())):

            self.tilt_warning()

    def _ball_ending_tilted(self, queue):
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

            self.ball_ending_tilted_queue.clear()

            self.machine.events.remove_handlers_by_keys(
                self.tilt_event_handlers)
            self.tilt_event_handlers = set()

    def tilt_settle_ms_remaining(self):
        """Return the amount of milliseconds remaining until the tilt settle time has cleared."""
        if not self.last_tilt_warning_switch:
            return 0

        delta = (self.tilt_config['settle_time'] -
                 (self.machine.clock.get_time() -
                  self.last_tilt_warning_switch) * 1000)
        if delta > 0:
            return delta
        else:
            return 0

    def slam_tilt(self):
        """Process a slam tilt."""
        self.machine.events.post('slam_tilt')
        '''event: slam_tilt
        desc: A slam tilt has just occurred.'''
        if not self.machine.game:
            return

        self.machine.game.slam_tilted = True
        self.machine.game.tilted = True
        self.tilt()
