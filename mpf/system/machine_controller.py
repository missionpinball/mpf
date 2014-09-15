"""The main machine object for the Mission Pinball Framework."""
# machine_controller.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import os
import yaml
from collections import defaultdict
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

    Attributes:
        options: A dictionary of options built from the command line options
        used to launch mpf.py.
    """
    def __init__(self, options):
        self.log = logging.getLogger("Machine Controller")
        self.log.info("Mission Pinball Framework v%s", version.__version__)
        self.options = options
        self.loop_start_time = 0
        self.config = defaultdict(int)  # so we can simplify checking
        self.physical_hw = options['physical_hw']
        self.switch_events = []
        self.done = False  # The machine run() loop will check this and exit if True
        self.HZ = None
        self.machineflow_index = None
        self.loop_rate = 0

        self.plugins = []
        self.scriptlets = []

        # load the MPF config & machine defaults
        self.load_config_yaml(self.options['mpfconfigfile'])

        # load the machine-specific config
        self.load_config_yaml(os.path.join(options['machinepath'],
                                           options['configfile']))
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

        self.events.post("machine_init_phase1")

        # Load the device modules
        self.config['MPF']['device_modules'] = (
            self.config['MPF']['device_modules'].split(' '))
        for device_type in self.config['MPF']['device_modules']:
            device_cls = eval(device_type)
            # Check to see if we have these types devices specific in this
            # machine's config file and only load the modules this machine uses.
            if device_cls.is_used(self.config):
                collection, config = device_cls.get_config_info()
                # create the collection
                exec('self.' + collection + '=devices.DeviceCollection()')
                devices.Device.create_devices(device_cls,
                                              eval('self.' + collection),
                                              self.config[config],
                                              self
                                              )

        self.events.post("machine_init_phase2")

        # Load plugins
        if 'Plugins' in self.config:
            self.config['Plugins'] = self.config['Plugins'].split(' ')
            for plugin in self.config['Plugins']:
                self.log.info("Loading Plugin: %s", plugin)
                i = __import__('mpf.plugins.' + plugin.split('.')[0],
                               fromlist=[''])
                self.plugins.append(getattr(i, plugin.split('.')[1])(self))

        # Add the machine path to our system path so we can import stuff from it
        sys.path.append(os.path.abspath(self.options['machinepath']))

        # Load Scriptlets
        if 'Scriptlets' in self.config:
            self.config['Scriptlets'] = self.config['Scriptlets'].split(' ')
            for scriptlet in self.config['Scriptlets']:
                i = __import__(self.config['MPF']['paths']['scriptlets'] + '.' +
                               scriptlet.split('.')[0], fromlist=[''])
                self.scriptlets.append(getattr(i, scriptlet.split('.')[1])
                                     (machine=self,
                                      name=scriptlet.split('.')[1]))

        # Configure the Machine Flow
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

        self.events.post("machine_init_phase3")

        self.reset()

    def reset(self):
        """Resets the machine."""
        self.events.post('machine_reset')
        # Do we want to reset all timers here? todo
        # do we post an event when we do this? Really this should re-read
        # the config and stuff, right? Maybe we destroy all of our objects
        # even and recreate them?

        # after our reset is over, we start the machineflow
        self.flow_advance(0)

    def flow_advance(self, position=None):
        """Advances the machine to the next machine mode as specified in the
        machineflow. Typically this just advances between Attract mode and Game
        mode.
        """
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
        self.config['MachineFlow'][self.machineflow_index].start()

    def load_config_yaml(self, config):
        """Merges config updates into the self.config dictionary.

        This method does what we call a "deep merge" which means it merges
        together subdictionaries instead of overwriting them. See the
        documentation for `meth:dict_merge` for a description of how this
        works.

        At this point this method loads YAML files, but it would be simple to
        load them from JSON, XML, INI, or existing python dictionaires.

        Args:
            config (dict or str) : The settings to deep merge into the config
                dictionary. If `config` is a dict, then it will merge those
                settings in. If it's a string, it will try to find a file with
                that name and open it to read in the settings.

                Also, if config is a string, it will first try to open it as a
                file directly (including any path that's there). If that
                doesn't work, it will try to open the file using the last path
                that worked. (This path is stored in
                `self.config['Config_path']`.)
        """
        new_updates = dict()
        #if not self.config['Config_path']:
        #    self.config['Config_path'] = ""
        if type(config) == dict:
            new_updates = config
        else:  # Maybe 'config' is a file?
            if os.path.isfile(config):
                config_location = config
                # Pull out the path in case we need it later
                self.config['Config_path'] = os.path.split(config)[0]
            elif os.path.isfile(os.path.join(self.config['Config_path'],
                                             config)):
                config_location = os.path.join(self.config['Config_path'],
                                               config)
            else:
                self.log.warning("Couldn't find config file: %s. Skipping.",
                                 config)
                config_location = ""

        if config_location:
            try:
                self.log.debug("Loading configuration from file: %s",
                               config_location)
                new_updates = yaml.load(open(config_location, 'r'))
            except yaml.YAMLError, exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    self.log.error("Error found in config file %s. Line %, "
                                   "Position %s", config_location, mark.line+1,
                                   mark.column+1)
                    quit()
            except:
                self.log.warning("Couldn't load config from file: %s", config)
                quit()

        self.config = self.dict_merge(self.config, new_updates)

        # now check if there are any more updates to do.
        # iterate and remove them
        if self.config['Config']:
            if config in self.config['Config']:
                self.config['Config'].remove(config)
            if self.config['Config']:
                self.load_config_yaml(self.config['Config'][0])

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
                quit()  # No point in continuing if we error here

        else:
            from mpf.platform.virtual import HardwarePlatform
            return HardwarePlatform(self)

    def string_to_list(self, string):
        """ Converts a comma-separated and/or space-separated string into a
        python list.

        Args:
            string (str): The string you'd like to convert.

        Returns:
            A python list object containing whatever was between commas in the
            string.
        """
        if type(string) is str:
            return string.replace(',', ' ').split()
        elif type(string) is list:
            # if it's already a list, do nothing
            return string
        else:
            # if we're not passed a string, just convert it to a list
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

    def enable_autofires(self):
        """Enables all the autofire coils in the machine."""

        self.log.debug("Enabling autofire coils")
        for autofire in self.autofires:
            autofire.enable()

    def disable_autofires(self):
        """Disables all the autofire coils in the machine."""

        self.log.debug("Disabling autofire coils")
        for autofire in self.autofires:
            autofire.disable()

    def enable_flippers(self):
        """Enables all the flippers in the machine."""
        self.log.debug("Enabling flippers")
        for flipper in self.flippers:
            flipper.enable()

    def disable_flippers(self):
        """Disables all the flippers in the machine."""
        self.log.debug("Disabling flippers")
        for flipper in self.flippers:
            flipper.disable()

    def run(self):
        """The main machine run loop."""
        self.log.debug("Starting the main machine run loop.")

        self.platform.timer_initialize()

        if self.platform.features['hw_timer']:
            self.platform.hw_loop()
        else:
            self.sw_loop()

        # todo add support to read software switch events

    def sw_loop(self):
        """ This is the main game run loop.

        """
        # todo currently this just runs as fast as it can. Should I have it
        # sleep while waiting for the next timer tick?

        self.log.debug("Starting the software loop")

        loop_start_time = time.time() - .01
        num_loops = 0

        while self.done is False:
            self.platform.hw_loop()
            if self.platform.next_tick_time <= time.time():  # todo change this
                self.timer_tick()
                self.platform.next_tick_time += timing.Timing.secs_per_tick
            num_loops += 1
            self.loop_rate = int(num_loops / (time.time() - loop_start_time))

        else:
            if num_loops != 0:
                self.log.info("Hardware loop speed: %sHz", self.loop_rate)

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
        self.done = True

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
