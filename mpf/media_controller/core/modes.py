""" """
# modes.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os

from collections import namedtuple

from mpf.system.timing import Timing, Timer
from mpf.system.tasks import DelayManager
from mpf.system.config import Config

RemoteMethod = namedtuple('RemoteMethod', 'method config_section kwargs',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""


class ModeController(object):
    """Parent class for the Mode Controller. There is one instance of this in
    MPF and it's responsible for loading, unloading, and managing all game
    modes.
    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('ModeController')

        self.active_modes = list()
        self.mode_stop_count = 0

        # The following two lists hold namedtuples of any remote components that
        # need to be notified when a mode object is created and/or started.
        self.loader_methods = list()
        self.start_methods = list()

        if 'Modes' in self.machine.config:
            self.machine.events.add_handler('mc_init_phase_4',
                                            self._load_modes)

    def _load_modes(self):
        #Loads the modes from the Modes: section of the machine configuration
        #file.

        for mode in self.machine.config['Modes']:
            self.machine.game_modes[mode] = self._load_mode(mode)

    def _load_mode(self, mode_string):
        """Loads a mode, reads in its config, and creates the Mode object.

        Args:
            mode: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.
        """
        self.log.info('Processing mode: %s', mode_string)

        mode_path = os.path.join(self.machine.machine_path,
            self.machine.config['MediaController']['paths']['modes'], mode_string)
        mode_config_file = os.path.join(self.machine.machine_path,
            self.machine.config['MediaController']['paths']['modes'],
            mode_string, 'config', mode_string + '.yaml')
        config = Config.load_config_yaml(yaml_file=mode_config_file)

        if 'code' in config['Mode']:

            import_str = ('modes.' + mode_string + '.code.' +
                          config['Mode']['code'].split('.')[0])
            i = __import__(import_str, fromlist=[''])
            mode_object = getattr(i, config['Mode']['code'].split('.')[1])(
                self.machine, config, mode_string, mode_path)

        else:
            mode_object = Mode(self.machine, config, mode_string, mode_path)

        return mode_object

    def register_load_method(self, load_method, config_section_name=None,
                             **kwargs):
        """Used by system components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when its
        registered.

        Args:
            load_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the load_method when
                it's called.
            **kwargs: Any additional keyword arguments specified will be passed
                to the load_method.

        Note that these methods will be called once, when the mode code is first
        initialized.
        """
        self.loader_methods.append(RemoteMethod(method=load_method,
            config_section=config_section_name, kwargs=kwargs))

    def register_start_method(self, start_method, config_section_name=None,
                              **kwargs):
        """Used by system components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when it starts.

        Args:
            start_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the start_method when
                it's called.
            **kwargs: Any additional keyword arguments specified will be passed
                to the start_method.

        Note that these methods will be called every single time this mode is
        started.
        """
        self.start_methods.append(RemoteMethod(method=start_method,
            config_section=config_section_name, kwargs=kwargs))

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

        self.log.info('================ ACTIVE GAME MODES ===================')

        for mode in self.active_modes:
            if mode.active:
                self.log.info('%s : %s', mode.name, mode.priority)

        self.log.info('======================================================')


class Mode(object):
    """Parent class for in-game mode code."""

    def __init__(self, machine, config, name, path):
        self.machine = machine
        self.config = config
        self.name = name
        self.path = path

        self.log = logging.getLogger('Mode.' + name)

        self.priority = 0
        self._active = False
        self.stop_methods = list()
        self.start_callback = None
        self.stop_callback = None
        self.event_handlers = set()

        if 'Mode' in self.config:
            self.configure_mode_settings(config['Mode'])

        for asset_manager in self.machine.asset_managers.values():

            config_data = self.config.get(asset_manager.config_section, dict())

            self.config[asset_manager.config_section] = (
                asset_manager.register_assets(config=config_data,
                                              mode_path=self.path))

        # Call registered remote loader methods
        for item in self.machine.modes.loader_methods:
            if (item.config_section in self.config and
                    self.config[item.config_section]):
                item.method(config=self.config[item.config_section],
                            mode_path=self.path,
                            **item.kwargs)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if self._active != active:
            self._active = active
            self.machine.modes._active_change(self, self._active)

    def configure_mode_settings(self, config):
        """Processes this mode's configuration settings from a config
        dictionary.
        """

        if not ('priority' in config and type(config['priority']) is int):
            config['priority'] = 0

        if 'start_events' in config:
            config['start_events'] = Config.string_to_list(
                config['start_events'])
        else:
            config['start_events'] = list()

        if 'stop_events' in config:
            config['stop_events'] = Config.string_to_list(
                config['stop_events'])
        else:
            config['stop_events'] = list()

        # register mode start events
        if 'start_events' in config:
            for event in config['start_events']:
                self.machine.events.add_handler(event, self.start)

        self.config['Mode'] = config

    def start(self, priority=None, callback=None, **kwargs):
        """Starts this mode.

        Args:
            priority: Integer value of what you want this mode to run at. If you
                don't specify one, it will use the "Mode: priority" setting from
                this mode's configuration file.
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode starts in the
        mode_start method which will be called automatically.
        """

        if type(priority) is int:
            self.priority = priority
        else:
            self.priority = self.config['Mode']['priority']

        self.log.info('Mode Start. Priority: %s', self.priority)

        # register mode stop events
        if 'stop_events' in self.config['Mode']:
            for event in self.config['Mode']['stop_events']:
                self.add_mode_event_handler(event, self.stop)

        self.active = True

        for item in self.machine.modes.start_methods:
            if item.config_section in self.config:
                self.stop_methods.append(
                    item.method(config=self.config[item.config_section],
                                priority=self.priority,
                                mode=self,
                                **item.kwargs))

        self.machine.events.post('mode_' + self.name + '_started')

    def stop(self, callback=None, **kwargs):
        """Stops this mode.

        Args:
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode stops in the
        mode_stop method which will be called automatically.
        """

        self.log.debug('Mode Stop.')

        self.priority = 0
        self.active = False

        for item in self.stop_methods:
            item[0](item[1])

        self.stop_methods = list()

        self.machine.events.post('mode_' + self.name + '_stopped')


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
