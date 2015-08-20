

import logging
from collections import OrderedDict
import yaml

from mpf.devices import *
from mpf.system.config import CaseInsensitiveDict, Config
from mpf.system.timing import Timing

class DeviceManager(object):

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("DeviceManager")
        self.log.info("Loading the Device Manager")

        self.collections = OrderedDict()
        self.device_classes = dict()  # collection_name: device_class
        self.mode_config_to_collection = dict()  # config_section: collection
        self.mode_config_sections = list() # list of tuples:
        # config_section, device class, collection
        self.mode_devices = dict()  # devices added in a mode config. mode:dev

        self._load_device_modules()

        self.machine.mode_controller.register_start_method(self._mode_start,
                                                           None, 100)

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

            self.mode_config_to_collection[device_cls.config_section] = collection

            if device_cls.allow_per_mode_devices:
                self.mode_config_sections.append(
                    (device_cls.config_section, device_cls, collection))

            self.collections[collection_name] = collection
            setattr(self.machine, collection_name, collection)

            # Get the config section for these devices
            config = self.machine.config.get(config, None)

            # create the devices
            if config:
                self.create_devices(collection_name, config)

            # create the machine-wide control events
            self.create_machine_control_events(collection, config)

            # create the default control events
            try:
                self._create_default_control_events(collection)
            except KeyError:
                pass

    def create_devices(self, collection, config):

        self.device_classes[collection].create_devices(
            cls=self.device_classes[collection],
            collection=getattr(self.machine, collection),
            config=config,
            machine=self.machine
            )

    def _mode_start(self, config, mode, priority=0):
        # Loops through the mode config to see if there are any device configs
        # for devices that have not been setup. If so, it sets them up. Returns
        # a list of the ones it set up so they can be removed when the mode ends
        # later.

        self._create_mode_devices(config, mode)
        self._create_mode_control_events(config, mode, priority)

        return  self._mode_stop, mode

    def _mode_stop(self, mode):
            self.remove_mode_devices(mode)

    def _create_mode_devices(self, config, mode):
        # Creates new devices that are specified in a mode config that haven't
        # been created in the machine-wide config

        # NOTE that devices created in modes

        if mode not in self.mode_devices:
            self.mode_devices[mode] = set()

        # i is tuple (config_section, device class, collection)
        for i in self.mode_config_sections:
            if i[0] in config:
                for device, settings in config[i[0]].iteritems():
                    if device not in i[2]:  # no existing device, create now

                        self.create_devices(i[2].name, {device: settings})

                        # change device from str to object
                        device = i[2][device]

                        # This lets the device know it was created by a mode
                        # instead of machine-wide, as some devices want to do
                        # certain things here.
                        device.device_added_to_mode(mode.player)

                        self.mode_devices[mode].add(device)

                        # Create the 'system' control events which is like
                        # <device_type>_<device_name>_reset or whatever...

                        event_prefix = (device.class_label + '_' +
                                        device.name + '_')
                        event_prefix2 = device.collection + '_'

                        for method in (self.machine.config['mpf']
                                ['device_events'][device.config_section]):

                            mode.add_mode_event_handler(
                                event=event_prefix + method,
                                handler=getattr(device, method))
                            mode.add_mode_event_handler(
                                event=event_prefix2 + method,
                                handler=getattr(device, method))

    def _create_mode_control_events(self, mode_config, mode, priority):
        # loop through all list of device configs to see if they contain control
        # events sections. Creates the control events if they do.

        for device_config_section in (
                self.machine.config['mpf']['device_events']):

            if device_config_section in mode_config:

                for device_name, device_settings in (
                        mode_config[device_config_section].iteritems()):

                    device = (self.mode_config_to_collection
                              [device_config_section][device_name])

                    for method in (
                            self.machine.config['mpf']['device_events']
                                               [device_config_section]):

                        config_setting = method + '_events'

                        if config_setting in device_settings:

                            for event, delay in Config.event_config_to_dict(
                                device_settings[config_setting]).iteritems():

                                # We use the mode event handler so it wil be
                                # removed when the mode ends. And we use the
                                # mode's delay manager so any remaining delays
                                # will be removed when the mode ends.
                                mode.add_mode_event_handler(
                                    event=event,
                                    handler=self._control_event_handler,
                                    callback=getattr(device, method),
                                    ms_delay=Timing.string_to_ms(delay),
                                    delay_mgr=mode.delay)

    def create_machine_control_events(self, collection, config):

        for device in collection:

            if device.config_section in (
                self.machine.config['mpf']['device_events']):

                for method in (
                        self.machine.config['mpf']['device_events']
                                           [device.config_section]):

                    config_setting = method + '_events'

                    # There's a machine-wide config entry for this control event
                    if config_setting in config[device.name]:
                        for event, delay in Config.event_config_to_dict(
                            config[device.name][config_setting]).iteritems():

                            self.machine.events.add_handler(
                                event=event,
                                handler=self._control_event_handler,
                                callback=getattr(device, method),
                                ms_delay=Timing.string_to_ms(delay),
                                delay_mgr=self.machine.delay)

                    # No machine-wide entry, so use the default(s)
                    else:
                        for event in Config.string_to_list(
                                self.machine.config['mpf']['device_events']
                                [device.config_section][method]):

                            self.machine.events.add_handler(
                                event=event,
                                handler=self._control_event_handler,
                                callback=getattr(device, method))


    def _control_event_handler(self, callback, ms_delay=0, delay_mgr=None,
                               **kwargs):
        if ms_delay:
            # name_target_reset
            delay_mgr.add(callback, ms_delay, callback)
        else:
            callback()

    def _create_default_control_events(self, device_list):
        for device in device_list:

            event_prefix = device.class_label + '_' + device.name + '_'
            event_prefix2 = device.collection + '_'

            for method in (self.machine.config['mpf']['device_events']
                           [device.config_section]):

                self.machine.events.add_handler(event=event_prefix + method,
                                                handler=getattr(device, method))
                self.machine.events.add_handler(event=event_prefix2 + method,
                                                handler=getattr(device, method))

    def remove_mode_devices(self, mode):

        for device in self.mode_devices.pop(mode, list()):
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
