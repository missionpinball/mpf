"""Contains the ModeController class for MPF."""
from collections import namedtuple

from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from mpf.core.events import QueuedEvent
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController

RemoteMethod = namedtuple('RemoteMethod', ['method', 'config_section', 'kwargs', 'priority'])
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.

"""


class ModeController(MpfController):

    """Responsible for loading, unloading, and managing all modes in MPF."""

    config_name = "mode_controller"

    __slots__ = ["queue", "active_modes", "mode_stop_count", "_machine_mode_folders", "_mpf_mode_folders",
                 "loader_methods", "start_methods"]

    def __init__(self, machine: MachineController) -> None:
        """initialize mode controller.

        Args:
        ----
            machine: The main MachineController instance.

        """
        super().__init__(machine)

        # ball ending event queue
        self.queue = None                           # type: Optional[QueuedEvent]

        self.active_modes = list()                  # type: List[Mode]
        self.mode_stop_count = 0

        self._machine_mode_folders = dict()         # type: Dict[str, str]
        self._mpf_mode_folders = dict()             # type: Dict[str, str]

        # The following two lists hold namedtuples of any remote components
        # that need to be notified when a mode object is created and/or
        # started.
        self.loader_methods = list()                # type: List[RemoteMethod]
        self.start_methods = list()                 # type: List[RemoteMethod]

        if 'modes' in self.machine.config:
            # priority needs to be higher than device_manager::_load_device_modules
            self.machine.events.add_async_handler('init_phase_1', self.load_modes, priority=10)
            self.machine.events.add_handler('init_phase_2', self.initialize_modes)

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
        for mode in self.machine.modes.values():
            mode.create_mode_devices()

    async def load_mode_devices(self):
        """Load mode devices."""
        for mode in self.machine.modes.values():
            await mode.load_mode_devices()

    def initialize_modes(self, **kwargs):
        """initialize modes."""
        del kwargs
        # initialize modes after loading all of them to prevent races
        for item in self.loader_methods:
            for mode in self.machine.modes.values():
                if (item.config_section and
                        item.config_section in mode.config and
                        mode.config[item.config_section]):
                    item.method(config=mode.config[item.config_section],
                                mode_path=mode.path,
                                mode=mode,
                                root_config_dict=mode.config,
                                **item.kwargs)
                elif not item.config_section:
                    item.method(config=mode.config, mode_path=mode.path,
                                **item.kwargs)

        for mode in self.machine.modes.values():
            mode.initialize_mode()

    async def load_modes(self, **kwargs):
        """Load the modes from the modes: section of the machine configuration file."""
        del kwargs

        for mode in set(self.machine.config['modes']):

            if mode in self.machine.modes.values():
                raise AssertionError('Mode {} already exists. Cannot load again.'.format(mode))

            # load mode
            self.machine.modes[mode] = self._load_mode(mode)

            self.log.debug("Loaded mode %s", mode)

    def _load_mode_config_spec(self, mode_string, mode_class):
        self.machine.config_validator.load_mode_config_spec(mode_string, mode_class.get_config_spec())

    @staticmethod
    def _load_mode_code(mode_string: str, code_path: str) -> Optional[Callable[..., Mode]]:
        """Load mode code.

        First try the full path and then prefix it with the mode name.
        """
        try:
            return Util.string_to_class(code_path)
        except ImportError:
            return Util.string_to_class("modes.{}.code.{}".format(mode_string, code_path))

    def _load_mode(self, mode_string) -> Mode:
        """Load a mode, reads in its config, and creates the Mode object.

        Args:
        ----
            mode_string: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.
        """
        self.debug_log('Processing mode: %s', mode_string)

        # Find the folder for this mode. First check the machine list, and if
        # it's not there, see if there's a built-in mpf mode

        config = self.machine.mpf_config.get_mode_config(mode_string)

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

        return mode_class(self.machine, config, mode_string, config['mode']['path'], config['mode']['asset_paths'])

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
        for mode in self.machine.modes.values():
            if not mode.is_game_mode:
                continue
            mode.player = player

    def _player_turn_ended(self, player, **kwargs):
        del kwargs
        del player
        for mode in self.machine.modes.values():
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
        ----
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
        self.loader_methods.sort(key=lambda x: x.priority, reverse=True)

    def register_start_method(self, start_method, config_section_name=None,
                              priority=0, **kwargs):
        """Register a method which is called anytime a mode is started.

        Used by core components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when it starts.

        Args:
        ----
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

    def set_mode_state(self, mode: Mode, active: bool):
        """Remember mode state."""
        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: (x.priority, x.name), reverse=True)

        # notify about changed active mode list
        self.machine.events.post("modes_active_modes_changed")
        '''event: modes_active_modes_changed

        The list of active mode changed. A mode has been started or stopped.
        '''

        if self._debug:
            self.dump()

    def dump(self):
        """Dump the current status of the running modes to the log file."""
        self.debug_log('+=========== ACTIVE MODES ============+')

        for mode in self.active_modes:
            if mode.active:
                self.debug_log('| {} : {}'.format(
                    mode.name, mode.priority).ljust(38) + '|')

        self.debug_log('+-------------------------------------+')

    def is_active(self, mode_name) -> bool:
        """Return true if the mode is active, False if it is not.

        Args:
        ----
            mode_name: String name of the mode to check.
        """
        return mode_name in [x.name for x in self.active_modes
                             if x.active is True]
