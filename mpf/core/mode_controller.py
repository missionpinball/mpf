"""Contains the ModeController class for MPF."""
import importlib
import logging
import os
from collections import namedtuple
from mpf.core.mode import Mode
from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util

RemoteMethod = namedtuple('RemoteMethod',
                          'method config_section kwargs priority',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.

"""

# Need to define RemoteMethod before import Mode since the mode module imports
# it. So this breaks some rules now. Probably should figure out some other way
# to do this? TODO


class ModeController(object):

    """Parent class for the Mode Controller.

    There is one instance of this in MPF and it's responsible for loading, unloading, and managing all modes.

    Args:
        machine: The main MachineController instance.

    """

    def __init__(self, machine):
        """Initialise mode controller."""
        self.machine = machine
        self.log = logging.getLogger('Mode Controller')

        self.debug = True

        self.queue = None  # ball ending event queue

        self.active_modes = list()
        self.mode_stop_count = 0

        self._machine_mode_folders = dict()
        self._mpf_mode_folders = dict()

        # The following two lists hold namedtuples of any remote components
        # that need to be notified when a mode object is created and/or
        # started.
        self.loader_methods = list()
        self.start_methods = list()
        self.stop_methods = list()

        if 'modes' in self.machine.config:
            self.machine.events.add_handler('init_phase_2',
                                            self._load_modes)

        self.machine.events.add_handler('ball_ending', self._ball_ending,
                                        priority=0)

        self.machine.events.add_handler('ball_starting', self._ball_starting,
                                        priority=0)

        self.machine.events.add_handler('player_add_success',
                                        self._player_added, priority=0)

        self.machine.events.add_handler('player_turn_start',
                                        self._player_turn_start,
                                        priority=1000000)

        self.machine.events.add_handler('player_turn_stop',
                                        self._player_turn_stop,
                                        priority=1000000)

    def _load_modes(self):
        # Loads the modes from the modes: section of the machine configuration
        # file.

        # todo if we get the config validator to validate files pre-merge, then
        # we can handle proper merging if people don't use dashes in their list
        # of modes

        self._build_mode_folder_dicts()

        for mode in set(self.machine.config['modes']):

            if mode not in self.machine.modes:
                self.machine.modes[mode] = self._load_mode(mode.lower())
            else:
                raise ValueError('Mode {} already exists. Cannot load again.'.
                                 format(mode))

    def _find_mode_path(self, mode_string):
        if mode_string in self._machine_mode_folders:
            return os.path.join(self.machine.machine_path,
                                self.machine.config['mpf']['paths']['modes'],
                                self._machine_mode_folders[mode_string])
        elif mode_string in self._mpf_mode_folders:
            return os.path.join(self.machine.mpf_path,
                                self.machine.config['mpf']['paths']['modes'],
                                self._mpf_mode_folders[mode_string])
        else:
            raise ValueError("No folder found for mode '{}'. Is your mode "
                             "folder in your machine's 'modes' folder?"
                             .format(mode_string))

    def _load_mode_config(self, mode_string):
        config = dict()
        # Is there an MPF default config for this mode? If so, load it first
        try:
            mpf_mode_config = os.path.join(
                self.machine.mpf_path,
                self.machine.config['mpf']['paths']['modes'],
                self._mpf_mode_folders[mode_string],
                'config',
                self._mpf_mode_folders[mode_string] + '.yaml')

            if os.path.isfile(mpf_mode_config):
                config = ConfigProcessor.load_config_file(mpf_mode_config,
                                                          config_type='mode')

                if self.debug:
                    self.log.debug("Loading config from %s", mpf_mode_config)

        except KeyError:
            pass

        # Now figure out if there's a machine-specific config for this mode,
        # and if so, merge it into the config
        try:
            mode_config_file = os.path.join(
                self.machine.machine_path,
                self.machine.config['mpf']['paths']['modes'],
                self._machine_mode_folders[mode_string],
                'config',
                self._machine_mode_folders[mode_string] + '.yaml')

            if os.path.isfile(mode_config_file):
                config = Util.dict_merge(config,
                                         ConfigProcessor.load_config_file(
                                             mode_config_file, 'mode'))

                if self.debug:
                    self.log.debug("Loading config from %s", mode_config_file)

        except KeyError:
            pass

        # validate config
        if 'mode' not in config:
            config['mode'] = dict()

        return config

    def _load_mode_config_spec(self, mode_string, mode_class):
        self.machine.config_validator.load_mode_config_spec(mode_string, mode_class.get_config_spec())

    def _load_mode(self, mode_string):
        """Load a mode, reads in its config, and creates the Mode object.

        Args:
            mode_string: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.
        """
        mode_string = mode_string.lower()

        if self.debug:
            self.log.debug('Processing mode: %s', mode_string)

        # Find the folder for this mode. First check the machine list, and if
        # it's not there, see if there's a built-in mpf mode

        mode_path = self._find_mode_path(mode_string)

        config = self._load_mode_config(mode_string)

        config['mode'] = self.machine.config_validator.validate_config("mode", config['mode'])

        # Figure out where the code is for this mode.
        if config['mode']['code']:
            try:  # First check the machine folder
                i = importlib.import_module(
                    self.machine.config['mpf']['paths']['modes'] + '.' +
                    self._machine_mode_folders[mode_string] + '.code.' +
                    config['mode']['code'].split('.')[0])

                mode_class = getattr(i, config['mode']['code'].split('.')[1])

                if self.debug:
                    self.log.debug("Loaded code from %s",
                                   self.machine.config['mpf']['paths']['modes'] + '.' +
                                   self._machine_mode_folders[mode_string] + '.code.' +
                                   config['mode']['code'].split('.')[0])

            except (KeyError, ImportError):     # code is in the mpf folder
                i = importlib.import_module(
                    'mpf.' + self.machine.config['mpf']['paths']['modes'] + '.' +
                    self._mpf_mode_folders[mode_string] + '.code.' +
                    config['mode']['code'].split('.')[0])

                mode_class = getattr(i, config['mode']['code'].split('.')[1])

                if self.debug:
                    self.log.debug("Loaded code from %s",
                                   'mpf.' + self.machine.config['mpf']['paths']['modes'] +
                                   '.' + self._mpf_mode_folders[mode_string] + '.code.' +
                                   config['mode']['code'].split('.')[0])

        else:  # no code specified, so using the default Mode class
            mode_class = Mode
            if self.debug:
                self.log.debug("Loaded default Mode() class code.")

        self._load_mode_config_spec(mode_string, mode_class)

        config['mode_settings'] = self.machine.config_validator.validate_config(
            "_mode_settings:{}".format(mode_string), config.get('mode_settings', None))

        return mode_class(self.machine, config, mode_string, mode_path)

    def _build_mode_folder_dicts(self):
        self._mpf_mode_folders = (
            self._get_mode_folder(self.machine.mpf_path))
        self.log.debug("Found MPF Mode folders: %s", self._mpf_mode_folders)

        self._machine_mode_folders = (
            self._get_mode_folder(self.machine.machine_path))
        self.log.debug("Found Machine-specific Mode folders: %s",
                       self._machine_mode_folders)

    def _get_mode_folder(self, base_folder):
        try:
            mode_folders = os.listdir(os.path.join(
                base_folder, self.machine.config['mpf']['paths']['modes']))
        except FileNotFoundError:
            return dict()

        final_mode_folders = dict()

        for folder in mode_folders:

            this_mode_folder = os.path.join(
                base_folder,
                self.machine.config['mpf']['paths']['modes'],
                folder)

            if os.path.isdir(this_mode_folder) and not folder.startswith('_'):
                final_mode_folders[folder.lower()] = folder

        return final_mode_folders

    @classmethod
    def _player_added(cls, player, num):
        del num
        player.restart_modes_on_next_ball = list()

    def _player_turn_start(self, player, **kwargs):
        del kwargs
        for mode in self.machine.modes:
            mode.player = player

    def _player_turn_stop(self, player, **kwargs):
        del kwargs
        del player
        for mode in self.machine.modes:
            mode.player = None

    def _ball_starting(self, queue):
        del queue
        for mode in self.machine.game.player.restart_modes_on_next_ball:
            self.log.debug("Restarting mode %s based on 'restart_on_next_ball"
                           "' setting", mode)

            mode.start()

        self.machine.game.player.restart_modes_on_next_ball = list()

    def _ball_ending(self, queue):
        # unloads all the active modes

        if not self.active_modes:
            return ()

        self.queue = queue
        self.queue.wait()
        self.mode_stop_count = 0

        for mode in self.active_modes:

            if mode.auto_stop_on_ball_end:
                self.mode_stop_count += 1
                mode.stop(callback=self._mode_stopped_callback)

            if mode.restart_on_next_ball:
                self.log.debug("Will Restart mode %s on next ball, mode")
                self.machine.game.player.restart_modes_on_next_ball.append(mode)

        if not self.mode_stop_count:
            self.queue.clear()

    def _mode_stopped_callback(self):
        self.mode_stop_count -= 1

        if not self.mode_stop_count:
            self.queue.clear()

    def register_load_method(self, load_method, config_section_name=None,
                             priority=0, **kwargs):
        """Register a method which is called when the mode is loaded.

        Used by core components, plugins, etc. to register themselves with
        the Mode Controller for anything they need a mode to do when it's
        registered.

        Args:
            load_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the load_method when
                it's called.
            priority: Int of the relative priority which allows remote methods
                to be called in a specific order. Default is 0. Higher values
                will be called first.
            **kwargs: Any additional keyword arguments specified will be passed
                to the load_method.

        Note that these methods will be called once, when the mode code is first
        initialized during the MPF boot process.
        """
        if not callable(load_method):
            raise ValueError("Cannot add load method '{}' as it is not"
                             "callable".format(load_method))

        self.loader_methods.append(RemoteMethod(method=load_method,
                                                config_section=config_section_name, kwargs=kwargs,
                                                priority=priority))

    def register_start_method(self, start_method, config_section_name=None,
                              priority=0, **kwargs):
        """Register a method which is called when the mode is started.

        Used by core components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when it starts.

        Args:
            start_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the start_method when
                it's called.
            priority: Int of the relative priority which allows remote methods
                to be called in a specific order. Default is 0. Higher values
                will be called first.
            **kwargs: Any additional keyword arguments specified will be passed
                to the start_method.

        Note that these methods will be called every single time this mode is
        started.
        """
        if not callable(start_method):
            raise ValueError("Cannot add start method '{}' as it is not"
                             "callable".format(start_method))

        if self.debug:
            self.log.debug('Registering %s as a mode start method. Config '
                           'section: %s, priority: %s, kwargs: %s',
                           start_method, config_section_name, priority, kwargs)

        self.start_methods.append(RemoteMethod(method=start_method,
                                               config_section=config_section_name, priority=priority,
                                               kwargs=kwargs))

        self.start_methods.sort(key=lambda x: x.priority, reverse=True)

    def register_stop_method(self, callback, priority=0):
        """Register a method which is called when the mode is stopped.

        These are universal, in that they're called every time a mode stops priority is the priority they're called.
        Has nothing to do with mode priority.
        """
        if not callable(callback):
            raise ValueError("Cannot add stop method '{}' as it is not"
                             "callable".format(callback))

        self.stop_methods.append((callback, priority))

        self.stop_methods.sort(key=lambda x: x[1], reverse=True)

    def set_mode_state(self, mode, active):
        """Called when a mode goes active or inactive."""
        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: x.priority, reverse=True)

        self.dump()

    def dump(self):
        """Dump the current status of the running modes to the log file."""
        self.log.debug('+=========== ACTIVE MODES ============+')

        for mode in self.active_modes:
            if mode.active:
                self.log.debug('| {} : {}'.format(
                    mode.name, mode.priority).ljust(38) + '|')

        self.log.debug('+-------------------------------------+')

    def is_active(self, mode_name):
        """Return true if the mode is active.

        Args:
            mode_name: String name of the mode to check.

        Returns:
            True if the mode is active, False if it is not.
        """
        return mode_name in [x.name for x in self.active_modes
                             if x.active is True]
