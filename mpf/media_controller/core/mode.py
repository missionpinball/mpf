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

class Mode(object):
    """Parent class for in-game mode code."""

    def __init__(self, machine, config, name, path):
        self.machine = machine
        self.config = config
        self.name = name.lower()
        self.path = path

        self.log = logging.getLogger('Mode.' + name)

        self.priority = 0
        self._active = False
        self.stop_methods = list()
        self.start_callback = None
        self.stop_callback = None
        self.event_handlers = set()

        if 'mode' in self.config:
            self.configure_mode_settings(config['mode'])

        for asset_manager in self.machine.asset_managers.values():

            config_data = self.config.get(asset_manager.config_section, dict())

            self.config[asset_manager.config_section] = (
                asset_manager.register_assets(config=config_data,
                                              mode_path=self.path))

        # Call registered remote loader methods
        for item in self.machine.mode_controller.loader_methods:
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
            self.machine.mode_controller._active_change(self, self._active)

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

        self.config['mode'] = config

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
            self.priority = self.config['mode']['priority']

        self.log.info('Mode Start. Priority: %s', self.priority)

        self.active = True

        for item in self.machine.mode_controller.start_methods:
            if item.config_section in self.config:
                self.stop_methods.append(
                    item.method(config=self.config[item.config_section],
                                priority=self.priority,
                                mode=self,
                                **item.kwargs))

        #self.machine.events.post('mode_' + self.name + '_started')

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
            try:
                item[0](item[1])
            except TypeError:
                pass

        self.stop_methods = list()

        #self.machine.events.post('mode_' + self.name + '_stopped')


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
