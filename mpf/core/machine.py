"""Contains the MachineController base class"""

import errno
import importlib
import logging
import os
import pickle
from pkg_resources import iter_entry_points
import queue
import sys
import threading

from mpf._version import __version__
from mpf.core.bcp import BCP
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.clock import ClockBase
from mpf.core.config_processor import ConfigProcessor
from mpf.core.config_validator import ConfigValidator
from mpf.core.data_manager import DataManager
from mpf.core.delays import DelayManager, DelayManagerRegistry
from mpf.core.device_manager import DeviceCollection
from mpf.core.utility_functions import Util


class MachineController(object):
    """Base class for the Machine Controller object.

    The machine controller is the main entity of the entire framework. It's the
    main part that's in charge and makes things happen.

    Args:
        options: Dictionary of options the machine controller uses to configure
            itself.

    Attributes:
        options: A dictionary of options built from the command line options
            used to launch mpf.py.
        config: A dictionary of machine's configuration settings, merged from
            various sources.
        done: Boolean. Set to True and MPF exits.
        machine_path: The root path of this machine_files folder
        plugins:
        scriptlets:
        hardware_platforms:
        events:

    """
    def __init__(self, mpf_path, machine_path, options):
        self.mpf_path = mpf_path
        self.machine_path = machine_path
        self.options = options
        self.log = logging.getLogger("Machine")
        self.log.info("Mission Pinball Framework v%s", __version__)
        self.log.debug("Command line arguments: %s", self.options)
        self.verify_system_info()

        self._boot_holds = set()
        self.register_boot_hold('init')
        self.clock = ClockBase()
        self.loop_start_time = 0
        self.tick_num = 0
        self.done = False
        self.monitors = dict()
        self.plugins = list()
        self.scriptlets = list()
        self.modes = DeviceCollection(self, 'modes', None)
        self.game = None
        self.active_debugger = dict()
        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False
        self.machine_var_data_manager = None
        self.thread_stopper = threading.Event()
        self.flag_bcp_reset_complete = False

        self.delayRegistry = DelayManagerRegistry(self)
        self.delay = DelayManager(self.delayRegistry)

        self.crash_queue = queue.Queue()
        self.clock.schedule_interval(self._check_crash_queue, 1)
        self.is_init_done = False
        self.config = None
        self.events = None
        self.machine_config = None
        self._set_machine_path()
        self._load_config()

        self.configure_debugger()

        self.config_validator = ConfigValidator(self)

        self.hardware_platforms = dict()
        self.default_platform = None

        if not self.options['force_platform']:
            for section, platform in self.config['hardware'].items():
                if platform.lower() != 'default' and section != 'driverboards':
                    self.add_platform(platform)
            self.set_default_platform(self.config['hardware']['platform'])

        else:
            self.add_platform(self.options['force_platform'])
            self.set_default_platform(self.options['force_platform'])

        # Do this here so there's a credit_string var even if they're not using
        # the credits mode
        try:
            credit_string = self.config['credits']['free_play_string']
        except KeyError:
            credit_string = 'FREE PLAY'

        self.create_machine_var('credits_string', credit_string, silent=True)

        self._load_core_modules()
        # order is specified in mpfconfig.yaml

        # This is called so hw platforms have a chance to register for events,
        # and/or anything else they need to do with core modules since
        # they're not set up yet when the hw platforms are constructed.
        for platform in list(self.hardware_platforms.values()):
            platform.initialize()

        self.validate_machine_config_section('machine')
        self.validate_machine_config_section('hardware')
        self.validate_machine_config_section('game')

        self._register_config_players()
        self._register_system_events()
        self._load_machine_vars()
        self.events.post("init_phase_1")
        self.events.process_event_queue()
        self.events.post("init_phase_2")
        self.events.process_event_queue()
        self._load_plugins()
        self.events.post("init_phase_3")
        self.events.process_event_queue()
        self._load_scriptlets()
        self.events.post("init_phase_4")
        self.events.process_event_queue()
        self.events.post("init_phase_5")
        self.events.process_event_queue()
        ConfigValidator.unload_config_spec()

        self.clear_boot_hold('init')

    @property
    def bcp_client_connected(self):
        return BCP.active_connections > 0

    def get_system_config(self):
        return self.machine_config['mpf']

    def validate_machine_config_section(self, section):

        # todo change this to use the normal process_config2 meth

        if section not in ConfigValidator.config_spec:
            return

        if section not in self.config:
            self.config[section] = dict()

        self.config[section] = self.config_validator.validate_config(
            section, self.config[section], section)

    def _register_system_events(self):
        self.events.add_handler('shutdown', self.power_off)
        self.events.add_handler(self.config['mpf']['switch_tag_event'].
                                replace('%', 'shutdown'), self.power_off)
        self.events.add_handler('quit', self.stop)
        self.events.add_handler(self.config['mpf']['switch_tag_event'].
                                replace('%', 'quit'), self.stop)

    def _register_config_players(self):
        # todo move this to config_player module
        for name, module in self.config['mpf']['config_players'].items():
            imported_module = importlib.import_module(module)
            setattr(self, '{}_player'.format(name),
                    imported_module.player_cls(self))

        self._register_plugin_config_players()

    def _register_plugin_config_players(self):

        for entry_point in iter_entry_points(group='mpf.config_player',
                                             name=None):
            entry_point.load()(self)

    def _load_machine_vars(self):
        self.machine_var_data_manager = DataManager(self, 'machine_vars')

        current_time = self.clock.get_time()

        for name, settings in (
                iter(self.machine_var_data_manager.get_data().items())):

            if ('expire' in settings and settings['expire'] and
                    settings['expire'] < current_time):

                settings['value'] = 0

            self.create_machine_var(name=name, value=settings['value'])

    def _check_crash_queue(self, time):
        del time
        try:
            crash = self.crash_queue.get(block=False)
        except queue.Empty:
            pass
        else:
            print("MPF Shutting down due to child thread crash")
            print("Crash details: %s", crash)
            self.stop()

    def _set_machine_path(self):
        self.log.debug("Machine path: %s", self.machine_path)

        # Add the machine folder to sys.path so we can import modules from it
        sys.path.insert(0, self.machine_path)

    def _load_config(self):
        if self.options['no_load_cache']:
            load_from_cache = False
        else:
            try:
                if self._get_latest_config_mod_time() > os.path.getmtime(os.path.join(
                        self.machine_path, '__mpfcache__', '{}_config.p'.
                        format('-'.join(self.options['configfile'])))):
                    load_from_cache = False  # config is newer
                else:
                    load_from_cache = True  # cache is newer

            except OSError as exception:
                if exception.errno != errno.ENOENT:
                    raise  # some unknown error?
                else:
                    load_from_cache = False  # cache file doesn't exist

        config_loaded = False
        if load_from_cache:
            config_loaded = self._load_config_from_cache()

        if not config_loaded:
            self._load_config_from_files()

    def _load_config_from_files(self):
        self.log.info("Loading config from original files")

        self.config = self._get_mpf_config()

        for num, config_file in enumerate(self.options['configfile']):

            if not (config_file.startswith('/') or
                    config_file.startswith('\\')):

                config_file = os.path.join(self.machine_path, self.config['mpf']['paths']['config'], config_file)

            self.log.info("Machine config file #%s: %s", num+1, config_file)

            self.config = Util.dict_merge(self.config,
                ConfigProcessor.load_config_file(config_file))
            self.machine_config = self.config

        if self.options['create_config_cache']:
            self._cache_config()

    def _get_mpf_config(self):
        return ConfigProcessor.load_config_file(self.options['mpfconfigfile'])

    def _load_config_from_cache(self):
        self.log.info("Loading cached config: %s",
                      os.path.join(self.machine_path, '__mpfcache__',
                                   '{}_config.p'.format('-'.join(self.options['configfile']))))

        with open(os.path.join(
                self.machine_path, '__mpfcache__', '{}_config.p'.
                format('-'.join(self.options['configfile']))), 'rb') as f:

            try:
                self.config = pickle.load(f)
                self.machine_config = self.config

            except:
                self.log.warning("Could not load config from cache")
                return False

            return True

    def _get_latest_config_mod_time(self):

        latest_time = os.path.getmtime(self.options['mpfconfigfile'])

        for root, dirs, files in os.walk(
                os.path.join(self.machine_path, 'config')):
            for name in files:
                if not name.startswith('.'):
                    if os.path.getmtime(os.path.join(root, name)) > latest_time:
                        latest_time = os.path.getmtime(os.path.join(root, name))

            for name in dirs:
                if not name.startswith('.'):
                    if os.path.getmtime(os.path.join(root, name)) > latest_time:
                        latest_time = os.path.getmtime(os.path.join(root, name))

        return latest_time

    def _cache_config(self):
        try:
            os.makedirs(os.path.join(self.machine_path, '__mpfcache__'))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        with open(os.path.join(
                self.machine_path, '__mpfcache__', '{}_config.p'.
                format('-'.join(self.options['configfile']))),
                'wb') as f:
            pickle.dump(self.config, f, protocol=4)
            self.log.info('Config file cache created: %s', os.path.join(
                self.machine_path, '__mpfcache__', '{}_config.p'.
                format('-'.join(self.options['configfile']))))

    def verify_system_info(self):
        """Dumps information about the Python installation to the log.

        Information includes Python version, Python executable, platform, and
        core architecture.

        """
        python_version = sys.version_info

        if not (python_version[0] == 3 and (
                        python_version[1] == 4 or python_version[1] == 5)):
            self.log.error("Incorrect Python version. MPF requires Python 3.4 "
                           "or 3.5. You have Python %s.%s.%s.",
                           python_version[0], python_version[1],
                           python_version[2])
            sys.exit()

        self.log.debug("Python version: %s.%s.%s", python_version[0],
                       python_version[1], python_version[2])
        self.log.debug("Platform: %s", sys.platform)
        self.log.debug("Python executable location: %s", sys.executable)
        self.log.debug("32-bit Python? %s", sys.maxsize < 2**32)

    def _load_core_modules(self):
        self.log.info("Loading core modules...")
        for name, module in self.config['mpf']['core_modules'].items():
            self.log.debug("Loading '%s' core module", module)
            m = Util.string_to_class(module)(self)
            setattr(self, name, m)

    def _load_plugins(self):
        self.log.info("Loading plugins...")

        # TODO: This should be cleaned up. Create a Plugins base class and
        # classmethods to determine if the plugins should be used.

        for plugin in Util.string_to_list(
                self.config['mpf']['plugins']):

            self.log.debug("Loading '%s' plugin", plugin)

            plugin_obj = Util.string_to_class(plugin)(self)
            self.plugins.append(plugin_obj)

    def _load_scriptlets(self):
        if 'scriptlets' in self.config:
            self.config['scriptlets'] = self.config['scriptlets'].split(' ')

            self.log.info("Loading scriptlets...")

            for scriptlet in self.config['scriptlets']:

                self.log.debug("Loading '%s' scriptlet", scriptlet)

                i = __import__(self.config['mpf']['paths']['scriptlets'] + '.' + scriptlet.split('.')[0], fromlist=[''])

                self.scriptlets.append(getattr(i, scriptlet.split('.')[1])
                                       (machine=self,
                                        name=scriptlet.split('.')[1]))

    def _prepare_to_reset(self):
        pass

        # wipe all event handlers

    def reset(self):
        """Resets the machine.

        This method is safe to call. It essentially sets up everything from
        scratch without reloading the config files and assets from disk. This
        method is called after a game ends and before attract mode begins.

        Note: This method is not yet implemented.

        """
        self.events.post('Resetting...')
        self.events.process_event_queue()
        self.events.post('machine_reset_phase_1')
        self.events.process_event_queue()
        self.events.post('machine_reset_phase_2')
        self.events.process_event_queue()
        self.events.post('machine_reset_phase_3')
        self.events.process_event_queue()
        self.log.debug('Reset Complete')
        self._reset_complete()

    def add_platform(self, name):
        """Makes an additional hardware platform interface available to MPF.

        Args:
            name: String name of the platform to add. Must match the name of a
                platform file in the mpf/platforms folder (without the .py
                extension).

        """

        if name not in self.hardware_platforms:

            try:
                hardware_platform = __import__('mpf.platforms.%s' % name,
                                               fromlist=["HardwarePlatform"])
            except ImportError:
                raise ImportError("Cannot add hardware platform {}. This is "
                                  "not a valid platform name".format(name))

            self.hardware_platforms[name] = (
                hardware_platform.HardwarePlatform(self))

    def set_default_platform(self, name):
        """Sets the default platform which is used if a device class-specific or
        device-specific platform is not specified. The default platform also
        controls whether a platform timer or MPF's timer is used.

        Args:
            name: String name of the platform to set to default.

        """
        try:
            self.default_platform = self.hardware_platforms[name]
            self.log.debug("Setting default platform to '%s'", name)
        except KeyError:
            self.log.error("Cannot set default platform to '%s', as that's not"
                           " a currently active platform", name)

    def register_monitor(self, monitor_class, monitor):
        """Registers a monitor.

        Args:
            monitor_class: String name of the monitor class for this monitor
                that's being registered.
            monitor: String name of the monitor.

        MPF uses monitors to allow components to monitor certain internal
        elements of MPF.

        For example, a player variable monitor could be setup to be notified of
        any changes to a player variable, or a switch monitor could be used to
        allow a plugin to be notified of any changes to any switches.

        The MachineController's list of registered monitors doesn't actually
        do anything. Rather it's a dictionary of sets which the monitors
        themselves can reference when they need to do something. We just needed
        a central registry of monitors.

        """
        if monitor_class not in self.monitors:
            self.monitors[monitor_class] = set()

        self.monitors[monitor_class].add(monitor)

    def run(self):
        """Starts the main machine run loop."""
        self.log.debug("Starting the main run loop.")

        self.default_platform.timer_initialize()

        self.loop_start_time = self.clock.get_time()

        self._run_loop()

    def stop(self):
        """Performs a graceful exit of MPF."""
        self.log.info("Shutting down...")
        self.events.post('shutdown')
        self.events.process_event_queue()
        self.thread_stopper.set()
        # todo change this to look for the shutdown event
        self.done = True

    def _run_loop(self):
        # Main machine run loop with when the default platform interface
        # specifies the MPF should control the main timer
        try:
            while not self.done:
                self.process_frame()
        except KeyboardInterrupt:
            pass

        self.log_loop_rate()
        self._platform_stop()

    def process_frame(self):
        """Processes the current frame and ticks the clock to wait for the
        next one"""
        # TODO: Replace the function call below
        # todo should the platforms register for their own ticks?
        self.default_platform.tick(self.clock.frametime)

        # Process events before processing the clock
        self.events.process_event_queue()

        # update dt
        self.clock.tick()

        # tick before draw
        self.clock.tick_draw()

    def _platform_stop(self):
        for platform in list(self.hardware_platforms.values()):
            platform.stop()

    def power_off(self):
        """Attempts to perform a power down of the pinball machine and ends MPF.

        This method is not yet implemented.
        """
        pass

    def log_loop_rate(self):
        self.log.info("Actual MPF loop rate: %s Hz",
                      round(self.clock.get_fps(), 2))

    # def _loading_tick(self, dt):
    #     if not self.asset_loader_complete:
    #
    #         if AssetManager.loader_queue.qsize():
    #             self.log.debug("Holding Attract start while MPF assets load. "
    #                            "Remaining: %s",
    #                            AssetManager.loader_queue.qsize())
    #             self.bcp.bcp_trigger('assets_to_load',
    #                  total=AssetManager.total_assets,
    #                  remaining=AssetManager.loader_queue.qsize())
    #         else:
    #             self.bcp.bcp_trigger('assets_to_load',
    #                  total=AssetManager.total_assets,
    #                  remaining=0)
    #             self.asset_loader_complete = True
    #
    #     elif self.bcp.active_connections and not self.flag_bcp_reset_complete:
    #         if self.tick_num % Timing.HZ == 0:
    #             self.log.info("Waiting for BCP reset_complete...")
    #
    #     else:
    #         self.log.debug("Asset loading complete")
    #         self._reset_complete()

    def bcp_reset_complete(self):
        self.flag_bcp_reset_complete = True

    def _reset_complete(self):
        self.log.debug('Reset Complete')
        self.events.post('reset_complete')
        # self.clock.unschedule(self._loading_tick)

    def configure_debugger(self):
        pass

    def get_debug_status(self, debug_path):

        if self.options['loglevel'] > 10 or self.options['consoleloglevel'] > 10:
            return True

        class_, module = debug_path.split('|')

        try:
            if module in self.active_debugger[class_]:
                return True
            else:
                return False
        except KeyError:
            return False

    def set_machine_var(self, name, value, force_events=False):
        """Sets the value of a machine variable.

        Args:
            name: String name of the variable you're setting the value for.
            value: The value you're setting. This can be any Type.
            force_events: Boolean which will force the event posting, the
                machine monitor callback, and writing the variable to disk (if
                it's set to persist). By default these things only happen if
                the new value is different from the old value.

        """
        if name not in self.machine_vars:
            self.log.warning("Received request to set machine_var '%s', but "
                             "that is not a valid machine_var.", name)
            return

        prev_value = self.machine_vars[name]['value']
        self.machine_vars[name]['value'] = value

        try:
            change = value-prev_value
        except TypeError:
            if prev_value != value:
                change = True
            else:
                change = False

        if change or force_events:

            if self.machine_vars[name]['persist'] and self.config['mpf']['save_machine_vars_to_disk']:
                disk_var = CaseInsensitiveDict()
                disk_var['value'] = value

                if self.machine_vars[name]['expire_secs']:
                    disk_var['expire'] = self.clock.get_time() + self.machine_vars[name]['expire_secs']

                self.machine_var_data_manager.save_key(name, disk_var)

            self.log.debug("Setting machine_var '%s' to: %s, (prior: %s, "
                           "change: %s)", name, value, prev_value,
                           change)
            self.events.post('machine_var_' + name,
                             value=value,
                             prev_value=prev_value,
                             change=change)

            if self.machine_var_monitor:
                for callback in self.monitors['machine_vars']:
                    callback(name=name, value=value,
                             prev_value=prev_value, change=change)

    def get_machine_var(self, name):
        """Returns the value of a machine variable.

        Args:
            name: String name of the variable you want to get that value for.

        Returns:
            The value of the variable if it exists, or None if the variable
            does not exist.

        """
        try:
            return self.machine_vars[name]['value']
        except KeyError:
            return None

    def is_machine_var(self, name):
        if name in self.machine_vars:
            return True
        else:
            return False

    def create_machine_var(self, name, value=0, persist=False,
                           expire_secs=None, silent=False):
        """Creates a new machine variable:

        Args:
            name: String name of the variable.
            value: The value of the variable. This can be any Type.
            persist: Boolean as to whether this variable should be saved to
                disk so it's available the next time MPF boots.
            expire_secs: Optional number of seconds you'd like this variable
                to persist on disk for. When MPF boots, if the expiration time
                of the variable is in the past, it will be loaded with a value
                of 0. For example, this lets you write the number of credits on
                the machine to disk to persist even during power off, but you
                could set it so that those only stay persisted for an hour.

        """
        var = CaseInsensitiveDict()

        var['value'] = value
        var['persist'] = persist
        var['expire_secs'] = expire_secs

        self.machine_vars[name] = var

        if not silent:
            self.set_machine_var(name, value, force_events=True)

    def remove_machine_var(self, name):
        """Removes a machine variable by name. If this variable persists to
        disk, it will remove it from there too.

        Args:
            name: String name of the variable you want to remove.

        """
        try:
            del self.machine_vars[name]
            self.machine_var_data_manager.remove_key(name)
        except KeyError:
            pass

    def remove_machine_var_search(self, startswith='', endswith=''):
        """Removes a machine variable by matching parts of its name.

        Args:
            startswith: Optional start of the variable name to match.
            endswith: Optional end of the variable name to match.

        For example, if you pass startswit='player' and endswith='score', this
        method will match and remove player1_score, player2_score, etc.

        """
        for var in list(self.machine_vars.keys()):
            if var.startswith(startswith) and var.endswith(endswith):
                del self.machine_vars[var]
                self.machine_var_data_manager.remove_key(var)

    def get_platform_sections(self, platform_section, overwrite):
        if not self.options['force_platform']:
            if not overwrite:
                if self.config['hardware'][platform_section] != 'default':
                    return self.hardware_platforms[self.config['hardware'][platform_section]]
                else:
                    return self.default_platform
            else:
                try:
                    return self.hardware_platforms[overwrite]
                except KeyError:
                    self.add_platform(overwrite)
                    return self.hardware_platforms[overwrite]
        else:
            return self.default_platform

    def register_boot_hold(self, hold):
        self._boot_holds.add(hold)

    def clear_boot_hold(self, hold):
        self._boot_holds.remove(hold)
        self.log.debug('Clearing boot hold %s. Holds remaining: %s', hold, self._boot_holds)
        if not self._boot_holds:
            self.init_done()

    def init_done(self):
        self.is_init_done = True
        ConfigValidator.unload_config_spec()
        self.reset()
