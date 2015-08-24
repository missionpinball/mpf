""" Contains the ShotProfileManager class."""
# shot_profile_manager.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import deque

from mpf.system.config import Config


class ShotProfileManager(object):

    def __init__(self, machine):

        self.machine = machine

        self.log = logging.getLogger('ShotProfileManager')

        self.profiles = dict()

        if 'shot_profiles' in self.machine.config:
            self.machine.events.add_handler('init_phase_3',
                self.register_profiles,
                config=self.machine.config['shot_profiles'])

        self.machine.mode_controller.register_load_method(
            self.register_profiles, config_section_name="shot_profiles")

        self.machine.mode_controller.register_start_method(
            self.apply_shot_profiles, config_section_name="shots")
        self.machine.mode_controller.register_start_method(
            self.apply_group_profiles, config_section_name="shot_groups")

        self.machine.events.add_handler('player_turn_start',
                                        self._player_turn_start,
                                        priority=1000000)
        self.machine.events.add_handler('player_turn_stop',
                                        self._player_turn_stop,
                                        priority=0)

    def register_profile(self, name, profile):
        """Registers a new shot profile with the shot controller which will
        allow it to be applied to shots.

        Args:
            name: String name of the profile you're registering.
            profile: Dict of the profile settings.

        """
        self.log.debug("Registering Shot Profile: '%s'", name)

        self.profiles[name] = self.process_profile_config(profile)

    def register_profiles(self, config, **kwargs):
        """Registers multiple shot profiles.

        Args:
            config: Dict containing the profiles you're registering. Keys are
                profile names, values are dictionaries of profile settings.

        """

        for name, profile in config.iteritems():
            self.register_profile(name, profile)

    def process_profile_config(self, config):
        """Processes a shot profile config to convert everything to the format
        the shot controller needs.

        Args:
            config: Dict of the profile settings to process.

        """

        config = self.machine.config_processor.process_config2(
            'shot_profiles', config, 'shot_profiles')

        rotation_pattern = deque()

        for entry in config['rotation_pattern']:
            if entry.upper() == 'R' or entry.upper() == 'RIGHT':
                rotation_pattern.append(1)
            else:
                rotation_pattern.append(-1)

        config['rotation_pattern'] = rotation_pattern

        return config

    def _player_turn_start(self, player, **kwargs):
        for shot in self.machine.shots:
            shot.player_turn_start(player)

    def _player_turn_stop(self, player, **kwargs):
        for shot in self.machine.shots:
            shot.player_turn_stop()

    def apply_shot_profiles(self, config, priority, mode, **kwargs):
        """Scans a config of shots looking for profile entries and applies any
        it finds to those shots.

        Args:
            config: Dict containing shot configurations.
            priority: Int of the priority these profiles will be applied at.
            mode: A Mode class which is the mode that's applying these shot
                profiles. This can be used later to remove the profiles when the
                mode ends.

        """
        for shot, settings in config.iteritems():
            if 'profile' in settings:
                self.machine.shots[shot].apply_profile(settings['profile'],
                                                           priority,
                                                           removal_key=mode)

        return self.remove_shot_profiles, mode

    def remove_shot_profiles(self, mode):
        """Removes all the shot profiles from all shots based on the mode
        passed.

        Args:
            mode: Mode class that will be used to determine which shot profiles
                will be removed.

        """
        for shot in self.machine.shots:
            shot.remove_profile_by_key(mode)

    def apply_group_profiles(self, config, priority, mode, **kwargs):
        """Applies profiles to member shots of a dict of shot groups.

        Args:
            config: Dict containing shot groups. Keys are shot group names.
                Values are settings for each shot group.
            priority: Int of the priority these profiles will be applied at.
            mode: A Mode class object for the mode which is applying these
                profiles. Used as the key to remove the profiles a specific mode
                applied later.

        """
        for shot_group, settings in config.iteritems():
            if 'profile' in settings:
                for shot in self.machine.shot_groups[shot_group].shots:
                    shot.apply_profile(settings['profile'], priority,
                                         removal_key=mode)

        return self.remove_group_profiles, mode

    def remove_group_profiles(self, mode):
        """Removes all the profiles that were applied to shots based on shot
        group settings in a mode.

        Args:
            mode: A Mode class which represents the mode that applied the
                profiles originally which will be used to determine which shot
                profiles should be removed.

        """
        for shot_group in self.machine.shot_groups:
            for shot in shot_group.shots:
                shot.remove_profile_by_key(mode)


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
