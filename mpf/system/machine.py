"""The main machine object for the Mission Pinball Framework."""
# machine.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import yaml
from collections import deque
from copy import deepcopy
import time
import sys

from mpf.system import *
from mpf.devices import *
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
        self.log = logging.getLogger("Machine")
        self.log.info("Mission Pinball Framework v%s", version.__version__)
        self.options = options
        self.loop_start_time = 0
        self.config = dict()
        self.physical_hw = options['physical_hw']
        self.switch_events = list()
        self.done = False
        self.machineflow_index = None
        self.loop_rate = 0.0
        self.mpf_load = 0.0
        self.machine_path = None  # Path to this machine's folder root

        self.plugins = list()
        self.scriptlets = list()
        self.game_modes = list()
        self.asset_managers = dict()

        # Get the Python version for the log
        python_version = sys.version_info
        self.log.info("Python version: %s.%s.%s", python_version[0],
                      python_version[1], python_version[2])
        self.log.info("Platform: %s", sys.platform)
        self.log.info("Python executable location: %s", sys.executable)
        self.log.info("32-bit Python? %s", sys.maxsize < 2**32)

        # load the MPF config & machine defaults
        self.config = self.load_config_yaml(config=self.config,
            yaml_file=self.options['mpfconfigfile'])

        # Find the machine_files location. If it starts with a forward or
        # backward slash, then we assume it's from the mpf root. Otherwise we
        # assume it's from the subfolder location specified in the
        # mpfconfigfile location

        if (options['machinepath'].startswith('/') or
                options['machinepath'].startswith('\\')):
            machine_path = options['machinepath']
        else:
            machine_path = os.path.join(self.config['MPF']['paths']
                                        ['machine_files'],
                                        options['machinepath'])

        self.machine_path = os.path.abspath(machine_path)

        # Add the machine folder to our path so we can import modules from it
        sys.path.append(self.machine_path)

        self.log.info("Machine folder: %s", machine_path)

        # Now find the config file location. Same as machine_file with the
        # slash uses to specify an absolute path

        if (options['configfile'].startswith('/') or
                options['configfile'].startswith('\\')):
            config_file = options['configfile']
        else:

            if not options['configfile'].endswith('.yaml'):
                options['configfile'] += '.yaml'

            config_file = os.path.join(machine_path,
                                       self.config['MPF']['paths']['config'],
                                       options['configfile'])

        self.log.info("Base machine config file: %s", config_file)

        # Load the machine-specific config
        self.config = self.load_config_yaml(config=self.config,
                                            yaml_file=config_file)

        self.platform = self.set_platform()

        # Load the system modules
        self.config['MPF']['system_modules'] = (
            self.config['MPF']['system_modules'].split(' '))
        for module in self.config['MPF']['system_modules']:
            self.log.info("Loading system module: %s", module)
            module_parts = module.split('.')
            exec('self.' + module_parts[0] + '=' + module + '(self)')

            # todo there's probably a more pythonic way to do this, and I know
            # exec() is supposedly unsafe, but meh, if you have access to put
            # malicious files in the system folder then you have access to this
            # code too.

        self.events.add_handler('action_shutdown', self.end_run_loop)
        self.events.add_handler('sw_shutdown', self.end_run_loop)
        self.events.add_handler('machine_reset_phase_3', self.flow_advance,
                                position=0)

        self.events.post("machine_init_phase_1")

        # Load the device modules
        self.config['MPF']['device_modules'] = (
            self.config['MPF']['device_modules'].split(' '))
        for device_type in self.config['MPF']['device_modules']:
            device_cls = eval(device_type)
            # Check to see if we have these types of devices specified in this
            # machine's config file and only load the modules this machine uses.
            if device_cls.is_used(self.config):
                collection, config = device_cls.get_config_info()

                # create the collection
                exec('self.' + collection + '=devices.DeviceCollection()')

                # Create this device
                devices.Device.create_devices(device_cls,
                                              eval('self.' + collection),
                                              self.config[config],
                                              self
                                              )

        self.events.post("machine_init_phase_2")

        # Load plugins
        if 'Plugins' in self.config:

            if type(self.config['Plugins']) is str:
                self.config['Plugins'] = self.config['Plugins'].split(' ')

            for plugin in self.config['Plugins']:
                self.log.info("Checking Plugin: %s", plugin)
                i = __import__('mpf.plugins.' + plugin.split('.')[0],
                               fromlist=[''])
                if i.preload_check(self):
                    self.log.info("Plugin: %s passes pre-load check. "
                                  "Loading...", plugin)
                    self.plugins.append(getattr(i, plugin.split('.')[1])(self))
                else:
                    self.log.warning("Plugin: %s failed pre-load check. "
                                     "Skipping.", plugin)

        self.events.post("machine_init_phase_3")

        # Load Scriptlets
        if 'Scriptlets' in self.config:
            self.config['Scriptlets'] = self.config['Scriptlets'].split(' ')

            for scriptlet in self.config['Scriptlets']:
                i = __import__(self.config['MPF']['paths']['scriptlets'] + '.'
                               + scriptlet.split('.')[0], fromlist=[''])

                self.scriptlets.append(getattr(i, scriptlet.split('.')[1])
                                       (machine=self,
                                        name=scriptlet.split('.')[1]))

        # Configure the Machine Flow
        self.log.debug("Configuring Machine Flow")
        self.config['MachineFlow'] = self.config['MachineFlow'].split(' ')
        # Convert the MachineFlow config into a list of objects
        i = 0
        for machine_mode in self.config['MachineFlow']:
            name = machine_mode.split('.')[-1:]
            self.config['MachineFlow'][i] = self.string_to_class(machine_mode)(
                                                                 self, name[0])
            i += 1
        # register event handlers
        self.events.add_handler('machineflow_advance', self.flow_advance)

        self.events.post("machine_init_phase_4")
        self.events.post("machine_init_phase_5")

        self.reset()

    def reset(self):
        """Resets the machine."""
        self.events.post('machine_reset_phase_1')
        self.events.post('machine_reset_phase_2')
        self.events.post('machine_reset_phase_3')
        # Do we want to reset all timers here? todo
        # do we post an event when we do this? Really this should re-read
        # the config and stuff, right? Maybe we destroy all of our objects
        # even and recreate them?

        # after our reset is over, we start the machineflow
        #self.flow_advance(0)

    def flow_advance(self, position=None, **kwargs):
        """Advances the machine to the next machine mode as specified in the
        machineflow. Typically this just advances between Attract mode and Game
        mode.
        """

        # This method will be called for the first time by the event
        # 'machine_reset_phase_3'

        # If there's a current machineflow position, stop that mode
        if self.machineflow_index is not None:
            self.config['MachineFlow'][self.machineflow_index].stop()
        else:
            self.machineflow_index = 0

        # Now find the new position and start it:
        if position is None:  # A specific position was not passed, so just advance
            if self.machineflow_index >= len(self.config['MachineFlow']) - 1:
                self.machineflow_index = 0
            else:
                self.machineflow_index += 1

        else:  # Go to whatever position was passed
            self.machineflow_index = position

        self.log.debug("Advancing Machine Flow. New Index: %s",
                       self.machineflow_index)

        # Now start the new machine mode
        self.config['MachineFlow'][self.machineflow_index].start(**kwargs)

    def load_config_yaml(self, config=None, yaml_file=None,
                         new_config_dict=None):
        """Merges a new config dictionary into an existing one.

        This method does what we call a "deep merge" which means it merges
        together subdictionaries instead of overwriting them. See the
        documentation for `meth:dict_merge` for a description of how this
        works.

        If the config dictionary you're merging in also contains links to
        additional config files, it will also merge those in.

        At this point this method loads YAML files, but it would be simple to
        load them from JSON, XML, INI, or existing python dictionaires.

        Args:
            config: The optional current version of the config dictionary that
                you're building up. If you don't pass a dictionary, this method
                will create one.
            yaml_file: A YAML file containing the settings to deep merge into
                the config dictionary. This method will try to find a file
                with that name and open it to read in the settings. It will
                first try to open it as a file directly (including any path
                that's there). If that doesn't work, it will try to open the
                file using the last path that worked. (This path is stored in
                `config['Config_path']`.)
            new_config_dict: A dictionary of settings to merge into the config
                dictionary.

        Note that you only need to specify a yaml_file or new_config_dictionary,
        not both.

        Returns: Python dictionary which is your source with all the new config
            options merged in.

        """

        if not config:
            config = dict()

        new_updates = dict()

        # If we were passed a config dict, load from there
        if type(new_config_dict) == dict:
            new_updates = new_config_dict

        # If not, do we have a yaml_file?
        elif yaml_file:
            if os.path.isfile(yaml_file):
                config_location = yaml_file
                # Pull out the path in case we need it later
                config['Config_path'] = os.path.split(yaml_file)[0]
            elif os.path.isfile(os.path.join(config['Config_path'],
                                             yaml_file)):
                config_location = os.path.join(config['Config_path'],
                                               yaml_file)
            else:
                self.log.critical("Couldn't find config file: %s.", yaml_file)
                raise Exception("Couldn't find config file: %s.", yaml_file)

        if config_location:
            try:
                self.log.info("Loading configuration from file: %s",
                              config_location)
                new_updates = yaml.load(open(config_location, 'r'))
            except yaml.YAMLError, exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    self.log.critical("Error found in config file %s. Line %s, "
                                      "Position %s", config_location,
                                      mark.line+1, mark.column+1)
                    raise Exception("Error found in config file %s. Line %s, "
                                    "Position %s", config_location,
                                    mark.line+1, mark.column+1)
            except:
                self.log.critical("Couldn't load config from file: %s",
                                  yaml_file)
                raise Exception("Couldn't load config from file: %s",
                                  yaml_file)

        config = self.dict_merge(config, new_updates)

        # now check if there are any more updates to do.
        # iterate and remove them

        try:
            if 'Config' in config:
                if yaml_file in config['Config']:
                    config['Config'].remove(yaml_file)
                if config['Config']:
                    config = self.load_config_yaml(config=config,
                                                   yaml_file=config['Config'][0])
        except:
            self.log.critical("No configuration file found, or config file is "
                              "empty. But congrats! Your game works! :)")
            raise Exception("No configuration file found, or config file is "
                            "empty. But congrats! Your game works! :)")

        return config

    def set_platform(self):
        """ Sets the hardware platform based on the "Platform" item in the
        configuration dictionary. Looks for a module of that name in the
        /platform directory.
        """

        if self.physical_hw:
            try:
                hardware_platform = __import__('mpf.platform.%s' %
                                   self.config['Hardware']['Platform'],
                                   fromlist=["HardwarePlatform"])
                # above line has an effect similar to:
                # from mpf.platform.<platform_name> import HardwarePlatform
                return hardware_platform.HardwarePlatform(self)

            except ImportError:
                self.log.error("Error importing platform module: %s",
                               self.config['Hardware']['Platform'])
                # do it again so the error shows up in the console. I forget
                # why we use 'try' here?
                hardware_platform = __import__('mpf.platform.%s' %
                                   self.config['Hardware']['Platform'],
                                   fromlist=["HardwarePlatform"])
                raise Exception("Error importing platform module: %s",
                                self.config['Hardware']['Platform'])
        else:
            from mpf.platform.virtual import HardwarePlatform
            return HardwarePlatform(self)

    def string_to_list(self, string):
        """ Converts a comma-separated and/or space-separated string into a
        python list.

        Args:
            string: The string you'd like to convert.

        Returns:
            A python list object containing whatever was between commas and/or
            spaces in the string.
        """
        if type(string) is str:
            return string.replace(',', ' ').split()
        elif type(string) is list:
            # if it's already a list, do nothing
            return string
        elif string is None:
            return []
        else:
            # if we're passed anything else, just make it into a list
            return [string]

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

    def dict_merge(self, a, b, combine_lists=True):
        """Recursively merges dictionaries.

        Used to merge dictionaries of dictionaries, like when we're merging
        together the machine configuration files. This method is called
        recursively as it finds sub-dictionaries.

        For example, in the traditional python dictionary
        update() methods, if a dictionary key exists in the original and
        merging-in dictionary, the new value will overwrite the old value.

        Consider the following example:

        Original dictionary:
        `config['foo']['bar'] = 1`

        New dictionary we're merging in:
        `config['foo']['other_bar'] = 2`

        Default python dictionary update() method would have the updated
        dictionary as this:

        `{'foo': {'other_bar': 2}}`

        This happens because the original dictionary which had the single key
        `bar` was overwritten by a new dictionary which has a single key
        `other_bar`.)

        But really we want this:

        `{'foo': {'bar': 1, 'other_bar': 2}}`

        This code was based on this:
        https://www.xormedia.com/recursively-merge-dictionaries-in-python/

        Args:
            a (dict): The first dictionary
            b (dict): The second dictionary
            combine_lists (bool):
                Controls whether lists should be combined (extended) or
                overwritten. Default is `True` which combines them.

        Returns:
            The merged dictionaries.
        """
        if not isinstance(b, dict):
            return b
        result = deepcopy(a)
        for k, v in b.iteritems():
            if k in result and isinstance(result[k], dict):
                result[k] = self.dict_merge(result[k], v)
            elif k in result and isinstance(result[k], list) and combine_lists:
                result[k].extend(v)
            else:
                result[k] = deepcopy(v)
        return result

    def run(self):
        """The main machine run loop."""
        self.log.debug("Starting the main machine run loop.")

        self.platform.timer_initialize()

        if self.platform.features['hw_timer']:
            self.platform.hw_loop()
        else:
            if 'Enable Loop Data' in self.config['Machine'] and (
                    self.config['Machine']['Enable Loop Data']):
                self.sw_data_loop()
            else:
                self.sw_optimized_loop()

        # todo add support to read software switch events

    def sw_optimized_loop(self):
        """The optimized version of the main game run loop."""

        self.log.debug("Starting the optimized software loop. Metrics are "
                       "disabled in this optimized loop.")
        self.mpf_load = 0
        self.loop_rate = 0
        start_time = time.time()
        loops = 0

        secs_per_tick = timing.Timing.secs_per_tick

        self.platform.next_tick_time = time.time()

        try:
            while self.done is False:
                self.platform.hw_loop()

                if self.platform.next_tick_time <= time.time():  # todo change this
                    self.timer_tick()
                    self.platform.next_tick_time += secs_per_tick
                    #sleep = (self.platform.next_tick_time - time.time()) / 1000.0
                    #if sleep > 0:
                    #    print sleep
                    #    time.sleep(sleep)
                    loops += 1

        except KeyboardInterrupt:
            pass

        self.log.info("Target loop rate: %s Hz", timing.Timing.HZ)
        self.log.info("Actual loop rate: %s Hz",
                      loops / (time.time() - start_time))

    def sw_data_loop(self):
        """ This is the main game run loop.

        """
        # todo currently this just runs as fast as it can. Should I have it
        # sleep while waiting for the next timer tick?

        self.log.debug("Starting the software loop")

        mpf_times = deque()
        hw_times = deque()

        mpf_times.extend([0] * 100)
        hw_times.extend([0] * 100)
        this_loop_time = 0
        hw_loop_time = 0

        try:
            while self.done is False:
                hw_entry = time.time()
                self.platform.hw_loop()
                hw_loop_time += time.time() - hw_entry
                if self.platform.next_tick_time <= time.time():

                    mpf_entry = time.time()
                    self.timer_tick()

                    try:
                        mpf_times.append((time.time() - mpf_entry) /
                                        (time.time() - this_loop_start))
                    except:
                        mpf_times.append(0.0)

                    try:
                        hw_times.append(hw_loop_time /
                                        (time.time() - this_loop_start))
                    except:
                        hw_times.append(0.0)

                    # throw away the oldest time
                    mpf_times.popleft()
                    hw_times.popleft()

                    # update our public info
                    self.mpf_load = round(sum(mpf_times), 2)
                    self.loop_rate = round(sum(hw_times), 2)

                    # reset the loop counter
                    hw_loop_time = 0.0
                    this_loop_start = time.time()

                    self.platform.next_tick_time += timing.Timing.secs_per_tick

        except KeyboardInterrupt:
            pass

        self.log.info("Hardware load percent: %s", self.loop_rate)
        self.log.info("MPF load percent: %s", self.mpf_load)

        # todo add detection to see if the system is running behind?
        # if you ask for 100HZ and the system can only do 50, that is
        # not good

    def timer_tick(self):
        """Called by the platform each machine tick based on self.HZ"""
        self.timing.timer_tick()  # notifies the timing module
        self.events.post('timer_tick')  # sends the timer_tick system event
        tasks.Task.timer_tick()  # notifies tasks
        tasks.DelayManager.timer_tick()

    def end_run_loop(self):
        """Causes the main run_loop to end."""
        self.log.info("Shutting down...")
        self.events.post('shutdown')
        self.done = True


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
