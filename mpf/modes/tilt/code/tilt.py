"""Contains the Tilt mode code"""

# tilt.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.config import CaseInsensitiveDict
from mpf.system.mode import Mode
from mpf.system.timing import Timing
import time


class Tilt(Mode):

    def mode_init(self):
        self._balls_to_collect = 0
        self._last_warning_tick = 0
        self.ball_ending_tilted_queue = None
        self.tilt_event_handlers = set()
        self.last_tilt_warning_switch = 0

        self.tilt_config = self.machine.config_processor.process_config2(
            config_spec='tilt',
            source=self._get_merged_settings('tilt'),
            section_name='tilt')

    def mode_start(self, **kwargs):
        self._register_switch_handlers()

        for event in self.tilt_config['reset_warnings_events']:
            self.add_mode_event_handler(event, self.reset_warnings)

    def mode_stop(self, **kwargs):
        self._remove_switch_handlers()
        self.reset_warnings_handlers = set()

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

    def tilt_warning(self):
        """Processes a tilt warning. If the number of warnings is the number to
        cause a tilt, a tilt will be processed.

        """
        self.last_tilt_warning_switch = time.time()

        if not self.player:
            return

        self.log.debug("Tilt Warning")

        self._last_warning_tick = self.machine.tick_num
        self.player[self.tilt_config['tilt_warnings_player_var']] += 1

        warnings = self.player[self.tilt_config['tilt_warnings_player_var']]

        if warnings >= self.tilt_config['warnings_to_tilt']:
            self.tilt()
        else:
            self.machine.events.post('tilt_warning',
                warnings=warnings,
                warnings_remaining=(self.tilt_config['warnings_to_tilt'] -
                                    warnings))
            self.machine.events.post('tilt_warning_{}'.format(warnings))

    def reset_warnings(self, **kwargs):
        """Resets the tilt warnings for the current player."""
        try:
            self.player[self.tilt_config['tilt_warnings_player_var']] = 0
        except AttributeError:
            pass

    def tilt(self, **kwargs):
        """Causes the ball to tilt."""
        if not self.machine.game:
            return

        self._balls_to_collect = self.machine.playfield.balls
        # todo use collection

        self.log.debug("Processing Tilt. Balls to collect: %s",
                       self._balls_to_collect)

        self.machine.game.tilted = True
        self.machine.events.post('tilt')
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
            else:
                self.tilt_event_handlers.add(
                    self.machine.events.add_handler(
                        'balldevice_{}_ball_enter'.format(device.name),
                        self._tilted_ball_entered_non_drain_device))

        self.machine.game.ball_ending()

    def _disable_flippers(self):
        for flipper in self.machine.flippers:
            flipper.disable()

    def _disable_autofires(self):
        for autofire in self.machine.autofires:
            autofire.disable()

    def _tilted_ball_drain(self, new_balls, unclaimed_balls, device):
        self._balls_to_collect -= unclaimed_balls

        self.log.debug("Tilted ball drain. Balls to collect: %s",
                       self._balls_to_collect)

        if self._balls_to_collect <= 0:
            self._tilt_done()

        return {'unclaimed_balls': 0}

    def _tilted_ball_entered_non_drain_device(self, new_balls, unclaimed_balls,
                                              device):
        return {'unclaimed_balls': unclaimed_balls}

    def _tilt_switch_handler(self):
        self.tilt()

    def _tilt_warning_switch_handler(self):
        if (self._last_warning_tick + self.tilt_config['multiple_hit_window']
                <= self.machine.tick_num):

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

            self.ball_ending_tilted_queue.clear()

            self.machine.events.remove_handlers_by_keys(self.tilt_event_handlers)
            self.tilt_event_handlers = set()

    def tilt_settle_ms_remaining(self):
        """Returns the amount of milliseconds remaining until the tilt settle
        time has cleared.

        """
        if not self.last_tilt_warning_switch:
            return 0

        delta = (time.time() - self.last_tilt_warning_switch -
                self.tilt_config['settle_time'])
        if delta > 0:
            return delta
        else:
            return 0

    def slam_tilt(self):
        self.machine.events.post('slam_tilt')
        self.game_ended()
