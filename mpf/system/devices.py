""" Contains the parent classes Device and DeviceCollection"""
# devices.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time
from collections import defaultdict
from mpf.system.timing import Timing


class Device(object):
    """ Generic parent class of for every hardware object in a pinball machine.

    """
    def __init__(self, machine, name, config=None, collection=-1):
        self.machine = machine
        self.name = name
        self.tags = list()
        self.label = None
        self.config = defaultdict(lambda: None, config)

        if config:
            self.config.update(config)
            if 'tags' in config:
                self.tags = self.machine.string_to_list(config['tags'])

            if 'label' in config:
                self.label = config['label']  # todo change to multi lang
            # todo more pythonic way, like self.label = blah if blah?

        # set event handlers to enable, disable, and reset this device
        # note that not all devices will use all of these methods

        # these lists of events can be strings or dicts

        if 'enable_events' in self.config:
            self.config['enable_events'] = self._event_config_to_dict(
                self.config['enable_events'])
        else:
            self.config['enable_events'] = dict()

        for event, delay in self.config['enable_events'].iteritems():
            self._create_events(ev_name=event,
                                ev_type='enable',
                                delay=delay,
                                callback=self.enable)

        if 'disable_events' in self.config:
            self.config['disable_events'] = self._event_config_to_dict(
                self.config['disable_events'])
        else:
            self.config['disable_events'] = dict()

        for event, delay in self.config['disable_events'].iteritems():
            self._create_events(ev_name=event,
                                ev_type='disable',
                                delay=delay,
                                callback=self.disable)

        if 'reset_events' in self.config:
            self.config['reset_events'] = self._event_config_to_dict(
                self.config['reset_events'])
        else:
            self.config['reset_events'] = dict()

        for event, delay in self.config['reset_events'].iteritems():
            self._create_events(ev_name=event,
                                ev_type='reset',
                                delay=delay,
                                callback=self.reset)

        # Add this instance to the collection for this type of device
        if collection != -1:
            # Have to use -1 here instead of None to catch an empty collection
            collection[name] = self

        #self.configure(config)

    @classmethod
    def is_used(cls, config):
        if cls.config_section in config:
            return True

    @classmethod
    def get_config_info(cls):
        return cls.collection, cls.config_section

    @staticmethod
    def create_devices(cls, collection, config, machine):
        # if this device class has a device_class_init staticmethod, run it now

        try:
            cls.device_class_init(machine)
        except:
            pass

        # create the devices
        for device in config:
            cls(machine, device, config[device], collection)

    def _event_config_to_dict(self, config):
        # processes the enable, disable, and reset events from the config file

        return_dict = dict()

        if type(config) is dict:
            return config
        elif type(config) is str:
            config = self.machine.string_to_list(config)

        # 'if' instead of 'elif' to pick up just-converted str
        if type(config) is list:
            for event in config:
                return_dict[event] = 0

        return return_dict

    def _create_events(self, ev_name, ev_type, delay, callback):

        self.log.debug("Creating %s_event handler for event '%s' with delay "
                       "'%s' husker", ev_type, ev_name, delay)

        self.machine.events.add_handler(event=ev_name,
                                    handler=self._action_event_handler,
                                    callback=callback,
                                    ms_delay=Timing.string_to_ms(delay))

    def _action_event_handler(self, ms_delay, callback, *args, **kwargs):
        if ms_delay:
            # name_target_reset
            self.delay.add(self.name + '_target_reset', ms_delay, callback)
        else:
            callback()

    def enable(self, *args, **kwargs):
        """Enables the device.

        This method is automatically called when one of the enable_events is
        posted. This is a placeholder method which does nothing. Implement it
        in the device subclass if you want to use it for that type of
        device."""
        pass

    def disable(self, *args, **kwargs):
        """Disables the device.

        This method is automatically called when one of the enable_events is
        posted. This is a placeholder method which does nothing. Implement it
        in the device subclass if you want to use it for that type of
        device."""
        pass

    def reset(self, *args, **kwargs):
        """Resets the device.

        This method is automatically called when one of the enable_events is
        posted. This is a placeholder method which does nothing. Implement it
        in the device subclass if you want to use it for that type of
        device."""
        pass


class DeviceCollection(dict):
    """A collection of Devices.

    One instance of this class will be created for each different type of
    hardware device (such as coils, lights, switches, ball devices, etc.)

    """

    def __getattr__(self, attr):
        # We use this to allow the programmer to access a hardware item like
        # self.coils.coilname

        try:
            # If we were passed a name of an item
            if type(attr) == str:
                return self[attr]
            elif type(attr) == int:
                self.number(number=attr)
        except KeyError:
            raise KeyError('Error: No device exists with the name:', attr)

        # todo there's something that's not working here that I need to figure
        # out. An example like this will fail:
        # self.hold_coil = self.machine.coils[config['hold_coil']]
        # even if config is a defaultdict, because config will return
        # None, and we can't call this DeviceCollection on None. Maybe make
        # default dict return some non-None as its default which we can catch
        # here?

    def __iter__(self):
        for item in self.itervalues():
            yield item

        # todo add an exception here if this isn't found?


    def items_tagged(self, tag):
        """Returns of list of device objects which have a certain tag.

        Args:
            tag: A string of the tag name which specifies what devices are
                returned.
        Returns:
            A list of device objects. If no devices are found with that tag, it
            will return an empty list.
        """
        output = []
        for item in self:
            if tag in item.tags:
                output.append(item)
        return output

    def is_valid(self, name):
        """Checks to see if the name passed is a valid device.

        Args:
            name: The string of the device name you want to check.
        Returns:
            True or False, depending on whether the name is a valid device or
            not.
        """
        if name in self.itervalues():
            return True
        else:
            return False

    def number(self, number):
        """Returns a device object based on its number."""
        for name, obj in self.iteritems():
            if obj.number == number:
                return self[name]



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
