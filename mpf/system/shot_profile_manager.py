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

        self.debug = True

    def register_profile(self, name, profile):
        """Registers a new shot profile with the shot controller which will
        allow it to be applied to shots.

        Args:
            name: String name of the profile you're registering.
            profile: Dict of the profile settings.

        """
        if self.debug:
            self.log.debug("Registering Shot Profile: '%s'", name)

        self.profiles[name] = self.process_profile_config(name, profile)

    def register_profiles(self, config, **kwargs):
        """Registers multiple shot profiles.

        Args:
            config: Dict containing the profiles you're registering. Keys are
                profile names, values are dictionaries of profile settings.

        """

        for name, profile in config.iteritems():
            self.register_profile(name, profile)

    def process_profile_config(self, profile_name, config):
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

        if not config['player_variable']:
            config['player_variable'] = '%_' + profile_name

        if self.debug:
            self.log.debug("Processed '%s' profile configuration: %s",
                           profile_name, config)

        return config

    def _player_turn_start(self, player, **kwargs):
        for shot in self.machine.shots:
            shot.player_turn_start(player)

    def _player_turn_stop(self, player, **kwargs):
        for shot in self.machine.shots:
            shot.player_turn_stop()

    def apply_shot_profiles(self, config, priority, mode, **kwargs):
        """ runs on mode start, sets the shots' enable_tables

        """
        if self.debug:
            self.log.debug("Scanning config from mode '%s' for shots",
                           mode.name)

        for shot, settings in config.iteritems():
            # is there a profile? yes, use it. no, use default
            if settings['profile']:
                profile = settings['profile']
            else:
                profile = self.machine.shots[shot].config['profile']

            # should this shot be enabled? are there enable events?
                # yes, do not enable
                # no, enable it now
            if settings['enable_events']:
                enable = False
            else:
                enable = True

            if self.debug:
                self.log.debug('Updating shot enable_table from config: profile'
                               ': %s, enable: %s, mode: %s', profile, enable,
                               mode)
                self.machine.shots[shot].log.debug('Updating shot enable_table '
                    'from config: profile: %s, enable: %s, mode: %s', profile,
                    enable, mode)

            self.machine.shots[shot].update_enable_table(profile, enable, mode)

        return self.remove_shot_profiles, mode

    def remove_shot_profiles(self, mode):
        """Runs on mode end

        """

        # pass the mode to remove it from the enable_table
        # get the shot to resort

        for shot in self.machine.shots:
            shot.remove_from_enable_table(mode)

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

        if self.debug:
            self.log.debug("Scanning config from mode '%s' for shot_groups",
                           mode.name)


        for shot_group, settings in config.iteritems():
            if settings['profile']:

                if self.debug:
                    self.log.debug("Found profile '%s' for shot_group '%s'",
                                   settings['profile'], shot_group)

                if settings['enable_events']:
                    enable = False
                else:
                    enable = True

                if self.debug:
                    self.log.debug("Updating shot_group's enable_table from "
                                   "config: profile: %s, enable: %s, mode: %s",
                                   settings['profile'], enable, mode)


                for shot in self.machine.shot_groups[shot_group].shots:

                    if self.debug:
                        shot.log.debug("Updating shot_group's enable_table from"
                                   " config: profile: %s, enable: %s, mode: %s",
                                   settings['profile'], enable, mode)

                    shot.update_enable_table(settings['profile'], enable, mode)

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
                shot.remove_from_enable_table(mode)


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
