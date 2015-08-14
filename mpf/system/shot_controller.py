""" Contains the ShotController class."""
# shot_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

from mpf.system.config import Config


class ShotController(object):

    def __init__(self, machine):

        self.machine = machine

        self.log = logging.getLogger('ShotController')

        self.profiles = dict()
        """shot_profiles dict:

        profile name : dict of settings

        settings dict:

        * loop: boolean
        * step_names_to_rotate: list
        * step_names_to_not_rotate: list
        * steps: list of tuples:
            name
            light_script
            lightshow

        '"""

        if 'shot_profiles' in self.machine.config:
            self.machine.events.add_handler('init_phase_3',
                self.register_profiles,
                config=self.machine.config['shot_profiles'])

        self.machine.mode_controller.register_load_method(
            self.register_profiles, config_section_name="shott_profiles")

        self.machine.mode_controller.register_start_method(
            self.apply_target_profiles, config_section_name="shots")
        self.machine.mode_controller.register_start_method(
            self.apply_group_profiles, config_section_name="shot_groups")

        self.machine.events.add_handler('player_turn_start',
                                        self._player_turn_start)
        self.machine.events.add_handler('player_turn_stop',
                                        self._player_turn_stop)

    def register_profile(self, name, profile):

        self.log.debug("Registering Shot Profile: '%s'", name)

        self.profiles[name] = self.process_profile_config(profile)

    def register_profiles(self, config, **kwargs):

        for name, profile in config.iteritems():
            self.register_profile(name, profile)

    def process_profile_config(self, config):

        config_spec = '''
                        step_names_to_rotate: list|None
                        step_names_to_not_rotate: list|None
                        loop: boolean|False
                        steps: list_of_dicts
                        player_variable: str|None
                        '''

        return Config.process_config(config_spec, config)

    def _player_turn_start(self, player, **kwargs):
        for shot in self.machine.shots:
            shot.player_turn_start(player)

        for drop_target in self.machine.drop_targets:
            drop_target.player_turn_start(player)

    def _player_turn_stop(self, player, **kwargs):
        for shot in self.machine.shots:
            shot.player_turn_stop()

        for drop_target in self.machine.drop_targets:
            drop_target.player_turn_stop()

    def apply_shot_profiles(self, config, priority, mode, **kwargs):
        for shot, settings in config.iteritems():
            if 'profile' in settings:
                self.machine.shots[shot].apply_profile(settings['profile'],
                                                           priority,
                                                           removal_key=mode)

        return self.remove_shot_profiles, mode

    def remove_shot_profiles(self, mode):
        for shot in self.machine.shots:
            shot.remove_profile(removal_key=mode)

    def apply_group_profiles(self, config, priority, mode, **kwargs):
        for shot_group, settings in config.iteritems():
            if 'profile' in settings:
                for shot in self.machine.shot_groups[shot_group].shots:
                    shot.apply_profile(settings['profile'], priority,
                                         removal_key=mode)

        return self.remove_group_profiles, mode

    def remove_group_profiles(self, mode):
        for shot_group in self.machine.shot_groups:
            for shot in shot_group.shots:
                shot.remove_profile(removal_key=mode)


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
