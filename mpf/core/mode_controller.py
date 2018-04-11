"""Contains the ModeController class for MPF."""
import importlib
import asyncio
import os
import tempfile
import hashlib
import errno
import pickle
from collections import namedtuple

from typing import Callable
from typing import Dict
from typing import List
from typing import Tuple
from typing import Optional

from mpf.core.events import QueuedEvent
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController

RemoteMethod = namedtuple('RemoteMethod', ['method', 'config_section', 'kwargs', 'priority'])
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.

"""


class ModeController(MpfController):

    """Responsible for loading, unloading, and managing all modes in MPF."""

    config_name = "mode_controller"

    def __init__(self, machine: MachineController) -> None:
        """Initialise mode controller.

        Args:
            machine: The main MachineController instance.

        """
        super().__init__(machine)

        # ball ending event queue
        self.queue = None                           # type: QueuedEvent

        self.active_modes = list()                  # type: List[Mode]
        self.mode_stop_count = 0

        self._machine_mode_folders = dict()         # type: Dict[str, str]
        self._mpf_mode_folders = dict()             # type: Dict[str, str]

        # The following two lists hold namedtuples of any remote components
        # that need to be notified when a mode object is created and/or
        # started.
        self.loader_methods = list()                # type: List[RemoteMethod]
        self.start_methods = list()                 # type: List[RemoteMethod]
        self.stop_methods = list()                  # type: List[Tuple[Callable[[Mode], None], int]]

        if 'modes' in self.machine.config:
            # priority needs to be higher than device_manager::_load_device_modules
            self.machine.events.add_async_handler('init_phase_1', self.load_modes, priority=10)
            self.machine.events.add_handler('init_phase_2', self.initialise_modes)

        self.machine.events.add_handler('ball_ending', self._ball_ending,
                                        priority=0)

        self.machine.events.add_handler('ball_starting', self._ball_starting,
                                        priority=0)

        self.machine.events.add_handler('player_added',
                                        self._player_added, priority=0)

        self.machine.events.add_handler('player_turn_started',
                                        self._player_turn_start,
                                        priority=1000000)

        self.machine.events.add_handler('player_turn_ended',
                                        self._player_turn_ended,
                                        priority=1000000)

    def create_mode_devices(self):
        """Create mode devices."""
        for mode in self.machine.modes:
            mode.create_mode_devices()

    def load_mode_devices(self):
        """Load mode devices."""
        for mode in self.machine.modes:
            mode.load_mode_devices()

    def initialise_modes(self, **kwargs):
        """Initialise modes."""
        del kwargs
        for mode in self.machine.modes:
            mode.initialise_mode()

    @asyncio.coroutine
    def load_modes(self, **kwargs):
        """Load the modes from the modes: section of the machine configuration file."""
        del kwargs

        self._build_mode_folder_dicts()

        for mode in set(self.machine.config['modes']):

            if mode in self.machine.modes:
                raise AssertionError('Mode {} already exists. Cannot load again.'.format(mode))

            # load mode
            self.machine.modes[mode] = self._load_mode(mode)

            # add a very very short yield to prevent hangs in platforms (e.g. watchdog timeouts during IO)
            yield from asyncio.sleep(.0001, loop=self.machine.clock.loop)
            self.log.debug("Loaded mode %s", mode)

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

    def _get_mpf_mode_config(self, mode_string):
        try:
            mpf_mode_config = os.path.join(
                self.machine.mpf_path,
                self.machine.config['mpf']['paths']['modes'],
                self._mpf_mode_folders[mode_string],
                'config',
                self._mpf_mode_folders[mode_string] + '.yaml')
            if not os.path.isfile(mpf_mode_config):
                return False
        except KeyError:
            return False

        return mpf_mode_config

    def _get_mode_config_file(self, mode_string):
        try:
            mode_config_file = os.path.join(
                self.machine.machine_path,
                self.machine.config['mpf']['paths']['modes'],
                self._machine_mode_folders[mode_string],
                'config',
                self._machine_mode_folders[mode_string] + '.yaml')
            if not os.path.isfile(mode_config_file):
                return False
        except KeyError:
            return False
        return mode_config_file

    def _load_mode_config(self, mode_string):
        config_files = []
        # Is there an MPF default config for this mode? If so, load it first
        mpf_mode_config = self._get_mpf_mode_config(mode_string)
        if mpf_mode_config:
            config_files.append(mpf_mode_config)

        # Now figure out if there's a machine-specific config for this mode,
        # and if so, merge it into the config
        mode_config_file = self._get_mode_config_file(mode_string)
        if mode_config_file:
            config_files.append(mode_config_file)

        if not config_files:
            raise AssertionError("Did not find any config for mode {}.".format(mode_string))

        config = self.machine.config_processor.load_config_files_with_cache(
            config_files, "mode", load_from_cache=not self.machine.options['no_load_cache'],
            store_to_cache=self.machine.options['create_config_cache'])

        if "mode" not in config:
            config["mode"] = dict()

        return config

    def _load_mode_config_spec(self, mode_string, mode_class):
        self.machine.config_validator.load_mode_config_spec(mode_string, mode_class.get_config_spec())

    def _load_mode_from_machine_folder(self, mode_string: str, code_path: str) -> Optional[Callable[..., Mode]]:
        """Load mode from machine folder and return it."""
        # this will only work for file_name.class_name
        try:
            file_name, class_name = code_path.split('.')
        except ValueError:
            return None

        # check if that mode name exist in machine folder
        if mode_string not in self._machine_mode_folders:
            return None

        # try to import
        try:
            i = importlib.import_module(
                self.machine.config['mpf']['paths']['modes'] + '.' +
                self._machine_mode_folders[mode_string] + '.code.' +
                file_name)
        except ImportError as e:
            # do not hide import error in mode
            if e.name != file_name:
                raise e
            return None

        return getattr(i, class_name, None)

    @staticmethod
    def _load_mode_from_full_path(code_path: str) -> Optional[Callable[..., Mode]]:
        """Load mode from full path.

        This is used for built-in modes like attract and game.
        """
        try:
            return Util.string_to_class(code_path)
        except ImportError as e:
            # do not hide import error in mode
            if e.name != code_path.split('.')[-1]:
                raise e
            return None

    def _load_mode_code(self, mode_string: str, code_path: str) -> Callable[..., Mode]:
        """Load code for mode."""
        # First check the machine folder
        mode_class = self._load_mode_from_machine_folder(mode_string, code_path)
        if mode_class:
            self.debug_log("Loaded code for mode %s from machine_folder", mode_string)
            return mode_class

        # load from full path
        mode_class = self._load_mode_from_full_path(code_path)
        if mode_class:
            self.debug_log("Loaded code for mode %s from full path", mode_string)
            return mode_class

        raise AssertionError("Could not load code for mode {} from {}".format(mode_string, code_path))

    def _load_mode(self, mode_string) -> Mode:
        """Load a mode, reads in its config, and creates the Mode object.

        Args:
            mode_string: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.
        """
        mode_string = mode_string

        self.debug_log('Processing mode: %s', mode_string)

        # Find the folder for this mode. First check the machine list, and if
        # it's not there, see if there's a built-in mpf mode

        mode_path = self._find_mode_path(mode_string)

        config = self._load_mode_config(mode_string)

        config['mode'] = self.machine.config_validator.validate_config("mode", config['mode'])

        # Figure out where the code is for this mode.
        if config['mode']['code']:
            # First check the machine folder
            mode_class = self._load_mode_code(mode_string, config['mode']['code'])

        else:  # no code specified, so using the default Mode class
            mode_class = Mode
            self.debug_log("Loaded default Mode() class code.")

        self._load_mode_config_spec(mode_string, mode_class)

        config['mode_settings'] = self.machine.config_validator.validate_config(
            "_mode_settings:{}".format(mode_string), config.get('mode_settings', None))

        return mode_class(self.machine, config, mode_string, mode_path)

    def _build_mode_folder_dicts(self):
        self._mpf_mode_folders = (
            self._get_mode_folder(self.machine.mpf_path))
        self.debug_log("Found MPF Mode folders: %s", self._mpf_mode_folders)

        self._machine_mode_folders = (
            self._get_mode_folder(self.machine.machine_path))
        self.debug_log("Found Machine-specific Mode folders: %s",
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
                final_mode_folders[folder] = folder

        return final_mode_folders

    @classmethod
    def _player_added(cls, player, num, **kwargs):
        del num
        del kwargs
        player.restart_modes_on_next_ball = list()
        '''player_var: restart_modes_on_next_ball

        desc: A list of modes that will be restarted when this player's next
        ball starts. This is more of an internal thing that MPF uses versus
        something that has a lot of value to you.
        '''

    def _player_turn_start(self, player, **kwargs):
        del kwargs
        for mode in self.machine.modes:
            if not mode.is_game_mode:
                continue
            mode.player = player

    def _player_turn_ended(self, player, **kwargs):
        del kwargs
        del player
        for mode in self.machine.modes:
            if not mode.is_game_mode:
                continue
            mode.player = None

    def _ball_starting(self, queue, **kwargs):
        del kwargs
        del queue
        for mode in self.machine.game.player.restart_modes_on_next_ball:
            self.debug_log("Restarting mode %s based on 'restart_on_next_ball"
                           "' setting", mode)

            mode.start()

        self.machine.game.player.restart_modes_on_next_ball = list()

    def _ball_ending(self, queue, **kwargs):
        """Unload all the active modes."""
        del kwargs

        if not self.active_modes:
            return

        self.queue = queue
        self.queue.wait()
        self.mode_stop_count = 0

        for mode in self.active_modes:

            if not mode.is_game_mode:
                continue

            if mode.auto_stop_on_ball_end:
                self.debug_log("Adding mode '%s' to ball ending queue", mode.name)
                self.mode_stop_count += 1
                mode.stop(callback=self._mode_stopped_callback)

            if mode.restart_on_next_ball:
                self.debug_log("Will Restart mode %s on next ball, mode")
                self.machine.game.player.restart_modes_on_next_ball.append(mode)

        if not self.mode_stop_count:
            self.queue.clear()

    def _mode_stopped_callback(self):
        self.mode_stop_count -= 1
        self.debug_log("Removing mode from ball ending queue")

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
        """Register a method which is called anytime a mode is started.

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

        """
        if not callable(start_method):
            raise ValueError("Cannot add start method '{}' as it is not"
                             "callable".format(start_method))

        self.debug_log('Registering %s as a mode start method. Config '
                       'section: %s, priority: %s, kwargs: %s',
                       start_method, config_section_name, priority, kwargs)

        self.start_methods.append(RemoteMethod(method=start_method,
                                               config_section=config_section_name, priority=priority,
                                               kwargs=kwargs))

        self.start_methods.sort(key=lambda x: x.priority, reverse=True)

    def remove_start_method(self, start_method, config_section_name=None, priority=0, **kwargs):
        """Remove an existing start method."""
        method = RemoteMethod(method=start_method, config_section=config_section_name,
                              priority=priority, kwargs=kwargs)

        if method in self.start_methods:
            self.start_methods.remove(method)

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

    def remove_stop_method(self, callback, priority=0):
        """Remove an existing stop method."""
        if (callback, priority) in self.stop_methods:
            self.stop_methods.remove((callback, priority))

    def set_mode_state(self, mode: Mode, active: bool):
        """Remember mode state."""
        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: x.priority, reverse=True)

        self.dump()

    def dump(self):
        """Dump the current status of the running modes to the log file."""
        self.debug_log('+=========== ACTIVE MODES ============+')

        for mode in self.active_modes:
            if mode.active:
                self.debug_log('| {} : {}'.format(
                    mode.name, mode.priority).ljust(38) + '|')

        self.debug_log('+-------------------------------------+')

    def is_active(self, mode_name):
        """Return true if the mode is active.

        Args:
            mode_name: String name of the mode to check.

        Returns:
            True if the mode is active, False if it is not.
        """
        return mode_name in [x.name for x in self.active_modes
                             if x.active is True]
