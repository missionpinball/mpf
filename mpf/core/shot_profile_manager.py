""" Contains the ShotProfileManager class."""

import logging
from collections import deque

from mpf.core.config_processor import ConfigProcessor


class ShotProfileManager(object):

    def __init__(self, machine):

        self.machine = machine

        self.log = logging.getLogger('ShotProfileManager')

        self.profiles = dict()

        self.debug = True

        if 'shot_profiles' in self.machine.config:
            self.register_profiles(config=self.machine.config['shot_profiles'])

        self.machine.mode_controller.register_load_method(
            self.register_profiles, config_section_name="shot_profiles")

        self.machine.mode_controller.register_start_method(
            self.mode_start_for_shots, config_section_name="shots", priority=1)
        self.machine.mode_controller.register_start_method(
            self.mode_start_for_shot_groups, config_section_name="shot_groups")

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
        if self.debug:
            self.log.debug("Registering Shot Profile: '%s'", name)

        self.profiles[name] = self.process_profile_config(name, profile)

    def register_profiles(self, config, **kwargs):
        """Registers multiple shot profiles.

        Args:
            config: Dict containing the profiles you're registering. Keys are
                profile names, values are dictionaries of profile settings.

        """

        for name, profile in config.items():
            self.register_profile(name, profile)

    def process_profile_config(self, profile_name, config):
        """Processes a shot profile config to convert everything to the format
        the shot controller needs.

        Args:
            config: Dict of the profile settings to process.

        """

        config = self.machine.config_validator.validate_config(
            'shot_profiles', config, 'shot_profiles')

        rotation_pattern = deque()

        for entry in config['rotation_pattern']:
            if entry.upper() == 'R' or entry.upper() == 'RIGHT':
                rotation_pattern.append('right')
            else:
                rotation_pattern.append('left')

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

    def mode_start_for_shots(self, config, priority, mode, **kwargs):
        """ runs on mode start, sets the shots' enable_tables

        """
        if self.debug:
            self.log.debug("Scanning config from mode '%s' for shots",
                           mode.name)

        for shot, settings in config.items():
            # is there a profile? yes, use it. no, use default
            if settings['profile']:
                profile = settings['profile']
            else:
                profile = self.machine.shots[shot].config['profile']

            if not settings['enable_events']:
                enable = True
            else:
                enable = False

            if settings['debug']:
                self.machine.shots[shot].enable_debugging()

            if self.debug:
                self.log.debug('Updating shot enable_table from config: profile'
                               ': %s, enable: %s, mode: %s', profile, enable,
                               mode)
                self.machine.shots[shot].log.debug('Updating shot enable_table '
                    'from config: profile: %s, enable: %s, mode: %s', profile,
                    enable, mode)

            self.machine.shots[shot].update_enable_table(profile, enable, mode)

        return self.mode_stop_for_shots, mode

    def mode_stop_for_shots(self, mode):
        """Runs on mode end

        """

        if self.debug:
            self.log.debug("Removing mode %s from all shots' enable_tables",
                           mode)

        # pass the mode to remove it from the enable_table

        for shot in self.machine.shots:
            shot.remove_from_enable_table(mode)

    def mode_start_for_shot_groups(self, config, priority, mode, **kwargs):
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
            self.log.debug("Scanning config %s for shot_groups", mode)

        for shot_group, settings in config.items():

            if self.debug:
                self.log.debug("Checking config for shot_group: %s. Config: %s",
                               shot_group, settings)

            if settings['debug']:
                self.machine.shot_groups[shot_group].enable_debugging()

            if not settings['enable_events']:

                if self.debug:
                    self.log.debug("No enable_events, enable entry will be "
                                   "True")
                enable = True
            else:

                if self.debug:
                    self.log.debug("Found enable_events, enable entry will be"
                                   " False")

                enable = False

            if self.debug:
                self.log.debug("Found profile '%s' for shot_group '%s'",
                               settings['profile'], shot_group)

            if self.debug:
                self.log.debug("Updating shot_group's enable_table from "
                               "config: profile: %s, mode: %s",
                               settings['profile'], mode)

            for shot in self.machine.shot_groups[shot_group].shots:
                if self.debug:
                    shot.log.debug("Updating enable_table from"
                               " config: profile: %s, enable: %s, mode: %s",
                               settings['profile'], enable, mode)

                shot.update_enable_table(settings['profile'], enable, mode)

        return self.mode_stop_for_shot_groups, mode

    def mode_stop_for_shot_groups(self, mode):
        """Removes all the profiles that were applied to shots based on shot
        group settings in a mode.

        Args:
            mode: A Mode class which represents the mode that applied the
                profiles originally which will be used to determine which shot
                profiles should be removed.

        """
        # todo this should be smarter and only run on shots that are not in
        # this mode's config? meh.. premature optimization though?

        for shot in self.machine.shots:
            shot.remove_from_enable_table(mode)
