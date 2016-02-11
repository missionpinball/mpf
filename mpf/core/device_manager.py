"""Contains the DeviceManager base class."""

import logging
from collections import OrderedDict

from mpf.core.utility_functions import Util
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.file_manager import FileManager


class DeviceManager(object):
    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("DeviceManager")

        self.collections = OrderedDict()
        self.device_classes = OrderedDict()  # collection_name: device_class

        self.machine.events.add_handler('init_phase_1',
                                        self._load_device_modules)

        self.machine.events.add_handler('init_phase_2',
                                        self.create_machinewide_device_control_events)

        self.machine.events.add_handler('init_phase_2',
                                        self.create_collection_control_events)

    def _load_device_modules(self):
        self.log.info("Loading devices...")
        self.machine.config['mpf']['device_modules'] = (
            self.machine.config['mpf']['device_modules'].split(' '))
        for device_type in self.machine.config['mpf']['device_modules']:

            device_cls = Util.string_to_class("mpf.devices." + device_type)

            collection_name, config = device_cls.get_config_info()

            self.device_classes[collection_name] = device_cls

            # create the collection
            collection = DeviceCollection(self.machine, collection_name,
                                          device_cls.config_section)

            self.collections[collection_name] = collection
            setattr(self.machine, collection_name, collection)

            # Get the config section for these devices
            config = self.machine.config.get(config, None)

            # create the devices
            if config:
                self.create_devices(collection_name, config)

            # create the default control events
            try:
                self._create_default_control_events(collection)
            except KeyError:
                pass

    def create_devices(self, collection, config, validate=True):

        self.device_classes[collection].create_devices(
                cls=self.device_classes[collection],
                collection=getattr(self.machine, collection),
                config=config,
                machine=self.machine,
                validate=validate
        )

    def get_device_control_events(self, config):
        """Scans a config dictionary and yields events, methods, delays, and
        devices for all the devices and control_events in that config.

        Args:
            config: An MPF config dictionary (either machine-wide or mode-
                specific).

        Returns:
            A generator of 4-item tuples:
                * The event name
                * The callback method of the device
                * The delay in ms
                * The device object

        """
        for collection in self.collections:
            if self.collections[collection].config_section in config:
                for device, settings in (iter(config[self.collections[collection].config_section].items())):

                    control_events = [x for x in settings if
                                      x.endswith('_events')]

                    for control_event in control_events:
                        # get events from this device's config
                        if settings[control_event]:
                            for event, delay in settings[control_event].items():
                                yield (event,
                                       getattr(self.collections
                                               [collection][device],
                                               control_event[:-7]),
                                       delay,
                                       self.collections[collection][device])

    def create_machinewide_device_control_events(self):

        for event, method, delay, _ in (
                self.get_device_control_events(self.machine.config)):

            try:
                event, priority = event.split('|')
            except ValueError:
                priority = 0

            self.machine.events.add_handler(
                    event=event,
                    handler=self._control_event_handler,
                    priority=int(priority),
                    callback=method,
                    ms_delay=delay,
                    delay_mgr=self.machine.delay)

    def create_collection_control_events(self):
        for collection, events in (iter(self.machine.config['mpf']['device_collection_control_events'].items())):

            for event in events:
                event_name = collection + '_' + event

                self.machine.events.add_handler(event_name,
                                                self._collection_control_event_handler,
                                                collection=collection,
                                                method=event)

    def _collection_control_event_handler(self, collection, method):
        for device in self.collections[collection]:
            getattr(device, method)()

    def _control_event_handler(self, callback, ms_delay=0, delay_mgr=None,
                               mode=None, **kwargs):
        del kwargs

        self.log.debug("_control_event_handler: mode: %s, callback: %s,", mode,
                       callback)

        if ms_delay:
            delay_mgr.add(ms=ms_delay, callback=callback, mode=mode)
        else:
            callback(mode=mode)

    def _create_default_control_events(self, device_list):
        for device in device_list:

            event_prefix = device.class_label + '_' + device.name + '_'
            event_prefix2 = device.collection + '_'

            for method in (self.machine.config['mpf']['device_events']
                           [device.config_section]):
                self.machine.events.add_handler(event=event_prefix + method,
                                                handler=getattr(device,
                                                                method))
                self.machine.events.add_handler(event=event_prefix2 + method,
                                                handler=getattr(device,
                                                                method))

    def save_tree_to_file(self, filename):
        print("Exporting file...")
        FileManager.save(filename, self.collections)
        print("Export complete!")


class DeviceCollection(CaseInsensitiveDict):
    """A collection of Devices.

    One instance of this class will be created for each different type of
    hardware device (such as coils, lights, switches, ball devices, etc.)

    """

    def __init__(self, machine, collection, config_section):
        super().__init__()

        self.machine = machine
        self.name = collection
        self.config_section = config_section

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
        for item in self.values():
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

    def sitems_tagged(self, tag):
        """Returns of list of device names (strings) which have a certain tag.

        Args:
            tag: A string of the tag name which specifies what devices are
                returned.
        Returns:
            A list of string names of devices. If no devices are found with
            that tag, it will return an empty list.
        """
        output = []
        for item in self:
            if tag in item.tags:
                output.append(item.name)
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
        if name.lower() in iter(self.values()):
            return True
        else:
            return False

    def number(self, number):
        """Returns a device object based on its number."""
        for name, obj in self.items():
            if obj.number == number:
                return self[name]
