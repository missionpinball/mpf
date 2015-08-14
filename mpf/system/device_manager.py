

import logging
from collections import OrderedDict
import yaml

from mpf.devices import *
from mpf.system.config import CaseInsensitiveDict

class DeviceManager(object):


    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("DeviceManager")
        self.log.info("Loading the Device Manager")

        self.collections = OrderedDict()
        self.device_classes = dict()
        self.mode_config_sections = list()

        self._load_device_modules()

        self.machine.mode_controller.register_start_method(self._mode_start, None, 100)

    def _load_device_modules(self):
        self.machine.config['mpf']['device_modules'] = (
            self.machine.config['mpf']['device_modules'].split(' '))
        for device_type in self.machine.config['mpf']['device_modules']:

            device_cls = eval(device_type)

            collection_name, config = device_cls.get_config_info()

            self.device_classes[collection_name] = device_cls


            # create the collection
            collection = DeviceCollection(self.machine, collection_name,
                                          device_cls.config_section)

            if device_cls.allow_per_mode_devices:
                self.mode_config_sections.append(
                    (device_cls.config_section, device_cls, collection))

            self.collections[collection_name] = collection
            setattr(self.machine, collection_name, collection)

            # create the devices

            if config or device_cls.allow_per_mode_devices:
                self.create_devices(collection_name,
                                    self.machine.config.get(config, None))
            else:
                self.log.debug("No '%s:' section found in machine configuration"
                               ", so this collection will not be created.",
                               config)

    def create_devices(self, collection, config):

        self.device_classes[collection].create_devices(
            cls=self.device_classes[collection],
            collection=getattr(self.machine, collection),
            config=config,
            machine=self.machine
            )

    def _mode_start(self, config, mode=None, priority=0):
        # Loops through the mode config to see if there are any device configs
        # for devices that have not been setup. If so, it sets them up. Returns
        # a list of the ones it set up so they can be removed when the mode ends
        # later.

        devices = set()

        # i is tuple (config_section, device class, collection)
        for i in self.mode_config_sections:
            if i[0] in config:

                for device, settings in config[i[0]].iteritems():

                    if device not in i[2]:  # no existing device, create now
                        self.create_devices(i[2].name, {device: settings})

                        # Have to do some things here since the player's turn
                        # has already started. Typically this creates the
                        # player attribute mapping and enables the device.
                        i[2][device].device_added_to_mode(mode.player)

                        devices.add(i[2][device])

        return  self.remove_devices, devices

    def remove_devices(self, devices):
        for device in devices:
            device.remove()

    def save_tree_to_file(self, filename):
        print "Exporting file..."

        with open(filename, 'w') as output_file:
            output_file.write(yaml.dump(self.collections,
                                        default_flow_style=False))

        print "Export complete!"


class DeviceCollection(CaseInsensitiveDict):
    """A collection of Devices.

    One instance of this class will be created for each different type of
    hardware device (such as coils, lights, switches, ball devices, etc.)

    """

    def __init__(self, machine, collection, config_section):
        super(DeviceCollection, self).__init__()

        self.machine = machine
        self.name = collection

        self.machine.mode_controller.register_start_method(self._register_control_events,
                                                 config_section)

    def _register_control_events(self, config, priority=0, mode=None):

        for device_name, device_settings in config.iteritems():
            device = getattr(self.machine, self.name)[device_name]

            key_list = device._create_control_events(device_settings,
                                                      mode.delay)

            return self._remove_control_events, key_list

    def _remove_control_events(self, key_list):

        self.machine.events.remove_handlers_by_keys(key_list)

    def __getattr__(self, attr):
        # We use this to allow the programmer to access a hardware item like
        # self.coils.coilname

        try:
            # If we were passed a name of an item
            if type(attr) == str:
                return self[attr.lower()]
            elif type(attr) == int:
                self.number(number=attr)
        except KeyError:
            raise KeyError('Error: No device exists with the name:', attr)

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

    def items_not_tagged(self, tag):
        """Returns of list of device objects which do not have a certain tag.

        Args:
            tag: A string of the tag name which specifies what devices are
                returned. All devices will be returned except those with this
                tag.
        Returns:
            A list of device objects. If no devices are found with that tag, it
            will return an empty list.
        """
        output = []
        for item in self:
            if tag not in item.tags:
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
        if name.lower() in self.itervalues():
            return True
        else:
            return False

    def number(self, number):
        """Returns a device object based on its number."""
        for name, obj in self.iteritems():
            if obj.number == number:
                return self[name]


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
