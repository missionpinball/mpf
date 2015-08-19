"""The main machine object for the Mission Pinball Framework."""
# machine.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import time
import sys
import Queue

from mpf.system import *
from mpf.system.config import Config
from mpf.system.tasks import Task, DelayManager
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
        machineflow_index: What machineflow position the machine is currently in.
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
        self.log_system_info()

        self.loop_start_time = 0
        self.tick_num = 0
        self.physical_hw = options['physical_hw']
        self.done = False
        self.machineflow_index = None
        self.machine_path = None  # Path to this machine's folder root
        self.monitors = dict()
        self.plugins = list()
        self.scriptlets = list()
        self.modes = list()
        self.asset_managers = dict()
        self.game = None

        self.num_assets_to_load = 0

        self.delay = DelayManager()

        self.crash_queue = Queue.Queue()
        Task.Create(self._check_crash_queue)

        self.config = dict()
        self._load_config()

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


        self._load_system_modules()
        self._register_system_events()
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

        self.log.info("Base machine config file: %s", config_file)

        # Load the machine-specific config
        self.config = Config.load_config_yaml(config=self.config,
                                            yaml_file=config_file)

    def log_system_info(self):
        """Dumps information about the Python installation to the log.

        Information includes Python version, Python executable, platform, and
        system architecture.

        """
        python_version = sys.version_info
        self.log.info("Python version: %s.%s.%s", python_version[0],
                      python_version[1], python_version[2])
        self.log.info("Platform: %s", sys.platform)
        self.log.info("Python executable location: %s", sys.executable)
        self.log.info("32-bit Python? %s", sys.maxsize < 2**32)

    def _load_system_modules(self):
        for module in self.config['mpf']['system_modules']:
            self.log.info("Loading '%s' system module", module[1])
            m = self.string_to_class(module[1])(self)
            setattr(self, module[0], m)
            # try:
            #     getattr(self, module[0]).post_init_callback()
            # except AttributeError:
            #     pass

    def _load_plugins(self):

        # TODO: This should be cleaned up. Create a Plugins superclass and
        # classmethods to determine if the plugins should be used.

        for plugin in Config.string_to_list(
                self.config['mpf']['plugins']):

            self.log.info("Loading '%s' plugin", plugin)

            i = __import__('mpf.plugins.' + plugin, fromlist=[''])
            self.plugins.append(i.plugin_class(self))

    def _load_scriptlets(self):
        if 'scriptlets' in self.config:
            self.config['scriptlets'] = self.config['scriptlets'].split(' ')

            for scriptlet in self.config['scriptlets']:

                self.log.info("Loading '%s' scriptlet", scriptlet)

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
        self.events.post('machine_reset_phase_1')
        self.events.post('machine_reset_phase_2')
        self.events.post('machine_reset_phase_3')
        self.log.info("Reset Complete")

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
