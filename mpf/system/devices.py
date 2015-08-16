""" Contains the parent classes Device and DeviceCollection"""
# devices.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from mpf.system.timing import Timing
from mpf.system.config import Config, CaseInsensitiveDict


class Device(object):
    """ Generic parent class of for every hardware device in a pinball machine.

    """

    allow_per_mode_devices = False

    def __init__(self, machine, name, config=None, collection=-1,
                 platform_section=None):
        self.machine = machine
        self.name = name.lower()
        self.tags = list()
        self.label = None
        self.debug = False
        self.platform = None
        self.config = dict()

        self.config = self.machine.config_processor.process_config2(
            'device:' + self.class_label, config, self.name)

        if self.config['debug']:
            self.debug = True
            self.log.debug("Enabling debug logging for this device")
            self.log.debug("Configuring device with settings: '%s'", config)

        self.tags = self.config['tags']
        self.label = self.config['label']

        if platform_section:
            if self.machine.physical_hw:
                if 'platform' not in config:
                    if self.machine.config['hardware'][platform_section] != 'default':
                        self.platform = (
                            self.machine.hardware_platforms
                            [self.machine.config['hardware'][platform_section]])
                    else:
                        self.platform = self.machine.default_platform
                else:
                    self.platform = (
                        self.machine.hardware_platforms[config['platform']])
            else:
                self.platform = self.machine.default_platform

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

        self._create_control_events(self.config, self.machine.delay)

        try:
            self._create_default_control_events(self.machine.config['mpf']
                                        ['device_events'][self.config_section])
        except KeyError:
            pass

        # Add this instance to the collection for this type of device
        if collection != -1:
            # Have to use -1 here instead of None to catch an empty collection
            collection[name] = self

    def __repr__(self):
        return '<' + self.class_label + '.' + self.name + '>'

    @classmethod
    def get_config_info(cls):
        return cls.collection, cls.config_section

    @staticmethod
    def create_devices(cls, collection, config, machine):
        # if this device class has a device_class_init classmethod, run it now
        if config and hasattr(cls, 'device_class_init'):
            # don't want to use try here in case the called meth has an error
            cls.device_class_init(machine)

        # create the devices

        if config:
            for device in config:
                cls(machine, device, config[device], collection)

    def _create_control_events(self, config, delay_manager=None):

        if not delay_manager:
            delay_manager = self.machine.delay

        event_keys = set()

        if self.config_section in self.machine.config['mpf']['device_events']:

            for method in (
                    self.machine.config['mpf']['device_events']
                                       [self.config_section]):

                config_setting = method + '_events'

                if config_setting in config:

                    for event, delay in self._event_config_to_dict(
                        config[config_setting]).iteritems():

                        event_keys.add(self.machine.events.add_handler(
                            event=event,
                            handler=self._control_event_handler,
                            callback=getattr(self, method),
                            ms_delay=Timing.string_to_ms(delay),
                            delay_mgr=delay_manager))

        return event_keys

    def _control_event_handler(self, ms_delay, callback, delay_mgr, **kwargs):
        if ms_delay:
            # name_target_reset
            delay_mgr.add(callback, ms_delay, callback)
        else:
            callback()

    def _event_config_to_dict(self, config):
        # processes the enable, disable, and reset events from the config file

        return_dict = dict()

        if type(config) is dict:
            return config
        elif type(config) is str:
            config = Config.string_to_list(config)

        # 'if' instead of 'elif' to pick up just-converted str
        if type(config) is list:
            for event in config:
                return_dict[event] = 0

        return return_dict

    def _create_default_control_events(self, config):
        # config is localized to this device's mpf:device_events section

        event_prefix = self.class_label + '_' + self.name + '_'
        event_prefix2 = self.collection + '_'

        for method in config:

            if config[method] and method + '_events' not in self.config:
                for event in Config.string_to_list(config[method]):
                    self.machine.events.add_handler(event=event,
                        handler=getattr(self, method))

            self.machine.events.add_handler(event=event_prefix + method,
                                            handler=getattr(self, method))
            self.machine.events.add_handler(event=event_prefix2 + method,
                                            handler=getattr(self, method))

    def device_added_to_mode(self, player):
        pass

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
