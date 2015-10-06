"""Contains the Tilt mode code"""

# tilt.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from collections import OrderedDict
from mpf.system.mode import Mode

class Tilt(Mode):

    def mode_init(self):
        self._balls_to_collect = 0
        self._last_warning_tick = 0

        self.tilt_config = self.machine.config['tilt']

        if 'tilt' in self.config:
            self.tilt_config.update(self.config['tilt'])

        self.tilt_config = self.machine.config_processor.process_config2(
            'tilt', self.tilt_config, 'tilt')

    def mode_start(self, **kwargs):
        self.add_mode_event_handler('tilt', self.tilt)
        self.add_mode_event_handler('slam_tilt', self.slam_tilt)
        self._register_switch_handlers()

    def mode_stop(self, **kwargs):
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

    def tilt_warning(self):
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
        self.player[self.tilt_config['tilt_warnings_player_var']] = 0

    def tilt(self):
        """Called when the 'tilt' event is posted indicated the ball has
        tilted.

        """
        self.log.debug("Processing Tilt")
        self._balls_to_collect = self.machine.playfield.balls
        self.balls_in_play = 0
        self._disable_autofires()
        self._disable_flippers()

        self.machine.events.add_handler('playfield_ball_count_change',
                                        self._tilted_pf_ball_count_change)
        self.machine.events.add_handler('tilted_all_balls_drained',
                                        self._tilted_all_balls_drained)
        self.machine.events.add_handler('ball_ending',
                                        self._ball_ending_tilted)

        self.machine.events.post('tilt')

    def _disable_flippers(self):
        for flipper in self.machine.flippers:
            flipper.disable()

    def _disable_autofires(self):
        for autofire in self.machine.autofires:
            autofire.disable()

    def _tilted_ball_drain(self, balls):
        self._balls_to_collect -= balls

        if self._balls_to_collect <= 0:
            self.machine.events.post('tilted_all_balls_drained')

        return {'balls': 0}

    def _tilted_all_balls_drained(self):
        # todo wait for settle time

        self.machine.game.ball_ending()

    def _tilt_switch_handler(self):
        pass

    def _tilt_warning_switch_handler(self):

        if (self._last_warning_tick + self.tilt_config['multiple_hit_window']
                <= self.machine.tick_num):

            self.tilt_warning()

    def _ball_ending_tilted(self):

        self.machine.post_queue('ball_ending_tilted',
                                self._ball_ending_tilted_ending_done)


        return False

    def _ball_ending_tilted_ending_done(self):
        self.machine.game._ball_ending_done()

        self.machine.events.remove_handler(self._ball_ending_tilted)

    def _tilted_pf_ball_count_change(self):
        pass


    def slam_tilt(self):
        self.game_ended()