import logging
import os
from collections import namedtuple

from mpf.system.config import Config


RemoteMethod = namedtuple('RemoteMethod', 'method config_section kwargs priority',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.

"""

# Need to define RemoteMethod before import Mode since the mode module imports
# it. So this breaks some rules now. Probably should figure out some other way
# to do this? TODO

from mpf.system.mode import Mode


class ModeController(object):
    """Parent class for the Mode Controller. There is one instance of this in
    MPF and it's responsible for loading, unloading, and managing all modes.

    Args:
        machine: The main MachineController instance.

    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('ModeController')

        self.queue = None  # ball ending event queue

        self.active_modes = list()
        self.mode_stop_count = 0

        # The following two lists hold namedtuples of any remote components that
        # need to be notified when a mode object is created and/or started.
        self.loader_methods = list()
        self.start_methods = list()

        if 'modes' in self.machine.config:
            self.machine.events.add_handler('init_phase_4',
                                            self._load_modes)

        self.machine.events.add_handler('ball_ending', self._ball_ending,
                                        priority=0)

        self.machine.events.add_handler('player_turn_start',
                                        self._player_turn_start,
                                        priority=1000000)

        self.machine.events.add_handler('player_turn_stop',
                                        self._player_turn_stop,
                                        priority=1000000)

    def _load_modes(self):
        #Loads the modes from the Modes: section of the machine configuration
        #file.

        for mode in self.machine.config['modes']:
            self.machine.modes.append(self._load_mode(mode))

    def _load_mode(self, mode_string):
        """Loads a mode, reads in its config, and creates the Mode object.

        Args:
            mode: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.

        """
        self.log.info('Processing mode: %s', mode_string)

        config = dict()

        # Is there an MPF default config for this mode? If so, load it first
        mpf_mode_config = os.path.join(
            'mpf',
            self.machine.config['mpf']['paths']['modes'],
            mode_string,
            'config',
            mode_string + '.yaml')

        if os.path.isfile(mpf_mode_config):
            config = Config.load_config_yaml(yaml_file=mpf_mode_config)

        # Now figure out if there's a machine-specific config for this mode, and
        # if so, merge it into the config
        mode_path = os.path.join(self.machine.machine_path,
            self.machine.config['mpf']['paths']['modes'], mode_string)
        mode_config_file = os.path.join(self.machine.machine_path,
            self.machine.config['mpf']['paths']['modes'], mode_string, 'config',
            mode_string + '.yaml')

        if os.path.isfile(mode_config_file):

            config = Config.load_config_yaml(config=config,
                                             yaml_file=mode_config_file)

        if 'code' in config['mode']:

            try:
                # Is the code for this mode in the machine folder?
                import_str = (self.machine.config['mpf']['paths']['modes'] +
                              '.' + mode_string + '.code.' +
                              config['mode']['code'].split('.')[0])
                i = __import__(import_str, fromlist=[''])

                self.log.info("Loading Mode class code from %s", import_str)

                mode_object = getattr(i, config['mode']['code'].split('.')[1])(
                    self.machine, config, mode_string, mode_path)

            except ImportError:
                # Is the code for this mode in the mpf folder?
                import_str = ('mpf.' +
                              self.machine.config['mpf']['paths']['modes'] +
                              '.' + mode_string + '.code.' +
                              config['mode']['code'].split('.')[0])
                i = __import__(import_str, fromlist=[''])

                self.log.info("Loading Mode class code from %s", import_str)

                mode_object = getattr(i, config['mode']['code'].split('.')[1])(
                    self.machine, config, mode_string, mode_path)

        else:
            self.log.info("Loading default Mode class code")
            mode_object = Mode(self.machine, config, mode_string, mode_path)

        return mode_object

    def _player_turn_start(self, player, **kwargs):

        for mode in self.machine.modes:
            mode.player = player

    def _player_turn_stop(self, player, **kwargs):

        for mode in self.machine.modes:
            mode.player = None

    def _ball_ending(self, queue):
        # unloads all the active modes

        if not self.active_modes:
            return()

        self.queue = queue
        self.queue.wait()
        self.mode_stop_count = 0

        for mode in self.active_modes:

            if mode.auto_stop_on_ball_end:

                self.mode_stop_count += 1
                mode.stop(callback=self._mode_stopped_callback)

    def _mode_stopped_callback(self):
        self.mode_stop_count -= 1

        if not self.mode_stop_count:
            self.queue.clear()

    def register_load_method(self, load_method, config_section_name=None,
                             priority=0, **kwargs):
        """Used by system components, plugins, etc. to register themselves with
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
        self.loader_methods.append(RemoteMethod(method=load_method,
            config_section=config_section_name, kwargs=kwargs,
            priority=priority))

    def register_start_method(self, start_method, config_section_name=None,
                              priority=0, **kwargs):
        """Used by system components, plugins, etc. to register themselves with
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
        self.start_methods.append(RemoteMethod(method=start_method,
            config_section=config_section_name, priority=priority,
            kwargs=kwargs))

        self.start_methods.sort(key=lambda x: x.priority, reverse=True)

    def _active_change(self, mode, active):
        # called when a mode goes active or inactive

        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: x.priority, reverse=True)

        self.dump()

    def dump(self):
        """Dumps the current status of the running modes to the log file."""

        self.log.info('================ ACTIVE MODES ===================')

        for mode in self.active_modes:
            if mode.active:
                self.log.info('%s : %s', mode.name, mode.priority)

        self.log.info('======================================================')
