""" Contains the TargetController class."""
# target_profile_manager.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging


class TargetController(object):

    def __init__(self, machine):

        self.machine = machine

        self.log = logging.getLogger('TargetController')

        self.profiles = dict()
        """target_profiles dict:

        profile name : dict of settings

        settings dict:

        * loop: boolean
        * steps: list of tuples:
            name
            light_script
            lightshow




        '"""

        if 'target_profiles' in self.machine.config:
            self.machine.events.add_handler('init_phase_3',
                self.register_profiles,
                config=self.machine.config['target_profiles'])

        self.machine.modes.register_load_method(
            self.register_profiles, config_section_name="target_profiles")

        self.machine.modes.register_start_method(
            self.apply_target_profiles, config_section_name="targets")
        self.machine.modes.register_start_method(
            self.apply_group_profiles, config_section_name="target_groups")

        self.machine.events.add_handler('player_turn_start',
                                        self._player_turn_start)

    def register_profile(self, name, profile):
        if 'reset_events' in profile:
            pass

        if 'loop' in profile:
            pass

        if 'steps' in profile:
            # for step in profile['steps']:
            #     step['name']
            #     step['light_script']
            #     step['lightshow']
            pass

        self.profiles[name] = profile

    def register_profiles(self, config, **kwargs):

        for name, profile in config.iteritems():
            self.register_profile(name, profile)

    def _player_turn_start(self, player, **kwargs):

        for target in self.machine.targets:
            target.player_turn_start(player)

    def apply_target_profiles(self, config, priority, mode, **kwargs):

        for target, settings in config.iteritems():
            if 'profile' in settings:
                self.machine.targets[target].apply_profile(settings['profile'],
                                                           priority,
                                                           removal_key=mode)

        return self.remove_target_profiles, mode

    def remove_target_profiles(self, mode):
        for target in self.machine.targets:
            target.remove_profile(removal_key=mode)

    def apply_group_profiles(self, config, priority, mode, **kwargs):
        for target_group, settings in config.iteritems():
            if 'target_profile' in settings:
                for target in self.machine.target_groups[target_group].targets:
                    target.apply_profile(settings['target_profile'], priority,
                                         removal_key=mode)

        return self.remove_group_profiles, mode

    def remove_group_profiles(self, mode):
        for target_group in self.machine.target_groups:
            for target in target_group.targets:
                target.remove_profile(removal_key=mode)






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
