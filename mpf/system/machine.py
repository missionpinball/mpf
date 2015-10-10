"""The main machine object for the Mission Pinball Framework."""
# machine.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import copy
import logging
import os
import time
import sys
import Queue

from mpf.system import *
from mpf.system.config import Config, CaseInsensitiveDict
from mpf.system.tasks import Task, DelayManager
from mpf.system.data_manager import DataManager
from mpf.system.timing import Timing
from mpf.system.assets import AssetManager
import version


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
        physical_hw: Boolean as to whether there is physical pinball controller
            hardware attached.
        done: Boolean. Set to True and MPF exits.
        machine_path: The root path of this machine_files folder
        display:
        plugins:
        scriptlets:
        tilted:
        platform:
        events:
    """
    def __init__(self, options):
        self.options = options
        self.log = logging.getLogger("Machine")
        self.log.info("Mission Pinball Framework v%s", version.__version__)
        self.verify_system_info()

        self.loop_start_time = 0
        self.tick_num = 0
        self.physical_hw = options['physical_hw']
        self.done = False
        self.machine_path = None  # Path to this machine's folder root
        self.monitors = dict()
        self.plugins = list()
        self.scriptlets = list()
        self.modes = list()
        self.asset_managers = dict()
        self.game = None
        self.active_debugger = dict()
        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False
        self.machine_var_data_manager = None

        self.flag_bcp_reset_complete = False
        self.asset_loader_complete = False

        self.delay = DelayManager()

        self.crash_queue = Queue.Queue()
        Task.create(self._check_crash_queue)

        self.config = dict()
        self._load_config()

        self.configure_debugger()

        self.hardware_platforms = dict()
        self.default_platform = None

        if self.physical_hw:
            for section, platform in self.config['hardware'].iteritems():
                if platform.lower() != 'default' and section != 'driverboards':
                        self.add_platform(platform)
        else:
            self.add_platform('virtual')

        if self.physical_hw:
            self.set_default_platform(self.config['hardware']['platform'])
        else:
            self.set_default_platform('virtual')

        # Do this here so there's a credit_string var even if they're not using
        # the credits mode
        self.create_machine_var('credits_string',
            self.config['credits']['free_play_string'], silent=True)

        self._load_system_modules()

        self.config['machine'] = self.config_processor.process_config2(
            'machine', self.config.get('machine', dict()), 'machine')

        self._register_system_events()
        self._load_machine_vars()
        self.events.post("init_phase_1")
        self.events.post("init_phase_2")
        self._load_plugins()
        self.events.post("init_phase_3")
        self._load_scriptlets()
        self.events.post("init_phase_4")
        self.events.post("init_phase_5")

        self.reset()

    def _register_system_events(self):
        self.events.add_handler('shutdown', self.power_off)
        self.events.add_handler(self.config['mpf']['switch_tag_event'].
                                replace('%', 'shutdown'), self.power_off)
        self.events.add_handler('quit', self.quit)
        self.events.add_handler(self.config['mpf']['switch_tag_event'].
                                replace('%', 'quit'), self.quit)
        self.events.add_handler('timer_tick', self._loading_tick)

    def _load_machine_vars(self):
        self.machine_var_data_manager = DataManager(self, 'machine_vars')

        current_time = time.time()

        for name, settings in (
                self.machine_var_data_manager.get_data().iteritems()):

            if ('expire' in settings and settings['expire'] and
                    settings['expire'] < current_time):

                settings['value'] = 0

            self.create_machine_var(name=name, value=settings['value'])

    def _check_crash_queue(self):
        try:
            crash = self.crash_queue.get(block=False)
        except Queue.Empty:
            yield 1000
        else:
            self.log.critical("MPF Shutting down due to child thread crash")
            self.log.critical("Crash details: %s", crash)
            self.done = True

    def _load_config(self):
        # creates the main config dictionary from the YAML machine config files.

        self.config = dict()

        # load the MPF config & machine defaults
        self.config = Config.load_config_yaml(config=self.config,
            yaml_file=self.options['mpfconfigfile'])

        # Find the machine_files location. If it starts with a forward or
        # backward slash, then we assume it's from the mpf root. Otherwise we
        # assume it's from the subfolder location specified in the
        # mpfconfigfile location

        if (self.options['machinepath'].startswith('/') or
                self.options['machinepath'].startswith('\\')):
            machine_path = self.options['machinepath']
        else:
            machine_path = os.path.join(self.config['mpf']['paths']
                                        ['machine_files'],
                                        self.options['machinepath'])

        self.machine_path = os.path.abspath(machine_path)

        # Add the machine folder to our path so we can import modules from it
        sys.path.append(self.machine_path)

        self.log.info("Machine folder: %s", machine_path)

        # Now find the config file location. Same as machine_file with the
        # slash uses to specify an absolute path

        if (self.options['configfile'].startswith('/') or
                self.options['configfile'].startswith('\\')):
            config_file = self.options['configfile']
        else:

            if not self.options['configfile'].endswith('.yaml'):
                self.options['configfile'] += '.yaml'

            config_file = os.path.join(machine_path,
                                       self.config['mpf']['paths']['config'],
                                       self.options['configfile'])

        self.log.debug("Base machine config file: %s", config_file)

        # Load the machine-specific config
        self.config = Config.load_config_yaml(config=self.config,
                                            yaml_file=config_file)

    def verify_system_info(self):
        """Dumps information about the Python installation to the log.

        Information includes Python version, Python executable, platform, and
        system architecture.

        """
        python_version = sys.version_info

        if python_version[0] != 2 or python_version[1] != 7:
            self.log.error("Incorrect Python version. MPF requires Python 2.7."
                           "x. You have Python %s.%s.%s.", python_version[0],
                           python_version[1], python_version[2])
            sys.exit()

        self.log.debug("Python version: %s.%s.%s", python_version[0],
                      python_version[1], python_version[2])
        self.log.debug("Platform: %s", sys.platform)
        self.log.debug("Python executable location: %s", sys.executable)
        self.log.debug("32-bit Python? %s", sys.maxsize < 2**32)

    def _load_system_modules(self):
        self.log.info("Loading system modules...")
        for module in self.config['mpf']['system_modules']:
            self.log.debug("Loading '%s' system module", module[1])
            m = self.string_to_class(module[1])(self)
            setattr(self, module[0], m)

    def _load_plugins(self):
        self.log.info("Loading plugins...")

        # TODO: This should be cleaned up. Create a Plugins superclass and
        # classmethods to determine if the plugins should be used.

        for plugin in Config.string_to_list(
                self.config['mpf']['plugins']):


            self.log.debug("Loading '%s' plugin", plugin)

            pluginObj = self.string_to_class(plugin)(self)
            self.plugins.append(pluginObj)

    def _load_scriptlets(self):
        if 'scriptlets' in self.config:
            self.config['scriptlets'] = self.config['scriptlets'].split(' ')

            self.log.info("Loading scriptlets...")

            for scriptlet in self.config['scriptlets']:

                self.log.debug("Loading '%s' scriptlet", scriptlet)

                i = __import__(self.config['mpf']['paths']['scriptlets'] + '.'
                               + scriptlet.split('.')[0], fromlist=[''])

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
        self.events.post('machine_reset_phase_1')
        self.events.post('machine_reset_phase_2')
        self.events.post('machine_reset_phase_3')
        self.log.debug('Reset Complete')

    def add_platform(self, name):
        """Makes an additional hardware platform interface available to MPF.

        Args:
            name: String name of the platform to add. Must match the name of a
                platform file in the mpf/platforms folder (without the .py
                extension).

        """

        if name not in self.hardware_platforms:
            hardware_platform = __import__('mpf.platform.%s' % name,
                                           fromlist=["HardwarePlatform"])
            self.hardware_platforms[name] = hardware_platform.HardwarePlatform(self)

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
            self.log.error("Cannot set default platform to '%s', as that's not "
                           "a currently active platform", name)

    def string_to_class(self, class_string):
        """Converts a string like mpf.system.events.EventManager into a python
        class.

        Args:
            class_string(str): The input string

        Returns:
            A reference to the python class object

        This function came from here:
        http://stackoverflow.com/questions/452969/
        does-python-have-an-equivalent-to-java-class-forname
        """
        parts = class_string.split('.')
        module = ".".join(parts[:-1])
        m = __import__(module)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m

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

        self.loop_start_time = time.time()

        if self.default_platform.features['hw_timer']:
            self.default_platform.run_loop()
        else:
            self._mpf_timer_run_loop()

    def _mpf_timer_run_loop(self):
        #Main machine run loop with when the default platform interface
        #specifies the MPF should control the main timer

        start_time = time.time()
        loops = 0
        secs_per_tick = timing.Timing.secs_per_tick
        sleep_sec = self.config['timing']['hw_thread_sleep_ms'] / 1000.0

        self.default_platform.next_tick_time = time.time()

        try:
            while self.done is False:
                time.sleep(sleep_sec)
                self.default_platform.tick()
                loops += 1
                if self.default_platform.next_tick_time <= time.time():  # todo change this
                    self.timer_tick()
                    self.default_platform.next_tick_time += secs_per_tick

        except KeyboardInterrupt:
            pass

        self.log_loop_rate()

        try:
            self.log.info("Hardware loop rate: %s Hz",
                          round(loops / (time.time() - start_time), 2))
        except ZeroDivisionError:
            self.log.info("Hardware loop rate: 0 Hz")

    def timer_tick(self):
        """Called to "tick" MPF at a rate specified by the machine Hz setting.

        This method is called by the MPF run loop or the platform run loop,
        depending on the platform. (Some platforms drive the loop, and others
        let MPF drive.)

        """
        self.tick_num += 1  # used to calculate the loop rate when MPF exits
        self.timing.timer_tick()  # notifies the timing module
        self.events.post('timer_tick')  # sends the timer_tick system event
        tasks.Task.timer_tick()  # notifies tasks
        tasks.DelayManager.timer_tick()

    def power_off(self):
        """Attempts to perform a power down of the pinball machine and ends MPF.

        This method is not yet implemented.
        """
        pass

    def quit(self):
        """Performs a graceful exit of MPF."""
        self.log.info("Shutting down...")
        self.events.post('shutdown')
        self.done = True

    def log_loop_rate(self):

        self.log.info("Target MPF loop rate: %s Hz", timing.Timing.HZ)

        try:
            self.log.info("Actual MPF loop rate: %s Hz",
                          round(self.tick_num /
                                (time.time() - self.loop_start_time), 2))
        except ZeroDivisionError:
            self.log.info("Actual MPF loop rate: 0 Hz")

    def _loading_tick(self):
        if not self.asset_loader_complete:

            if AssetManager.loader_queue.qsize():
                self.log.debug("Holding Attract start while MPF assets load. "
                               "Remaining: %s", AssetManager.loader_queue.qsize())
                self.bcp.bcp_trigger('assets_to_load',
                                     total=AssetManager.total_assets,
                                     remaining=AssetManager.loader_queue.qsize())
            else:
                self.bcp.bcp_trigger('assets_to_load',
                                     total=AssetManager.total_assets,
                                     remaining=0)
                self.asset_loader_complete = True

        elif self.bcp.active_connections and not self.flag_bcp_reset_complete:
            if self.tick_num % Timing.HZ == 0:
                self.log.info("Waiting for BCP reset_complete...")

        else:
            self.log.debug("Asset loading complete")
            self._reset_complete()

    def bcp_reset_complete(self):
        self.flag_bcp_reset_complete = True

    def _reset_complete(self):
        self.log.debug('Reset Complete')
        self.events.post('reset_complete')
        self.events.remove_handler(self._loading_tick)

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

            if self.machine_vars[name]['persist']:
                disk_var = CaseInsensitiveDict()
                disk_var['value'] = value

                if self.machine_vars[name]['expire_secs']:
                    disk_var['expire'] = (time.time() +
                        self.machine_vars[name]['expire_secs'])

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
        for var in self.machine_vars.keys():
            if var.startswith(startswith) and var.endswith(endswith):
                del self.machine_vars[var]
                self.machine_var_data_manager.remove_key(var)



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
