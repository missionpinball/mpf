"""Contains the DeviceManager base class."""

import logging
from collections import OrderedDict

from mpf.core.utility_functions import Util
from mpf.core.case_insensitive_dict import CaseInsensitiveDict


class DeviceManager(object):

    """Manages devices in a MPF machine."""

    def __init__(self, machine):
        """Initialise device manager."""
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
        self.log.debug("Loading devices...")
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

        self.load_devices_config(validate=True)
        self.initialize_devices()

    def create_devices(self, collection_name, config):
        """Create devices for collection."""
        cls = self.device_classes[collection_name]

        collection = getattr(self.machine, collection_name)

        # if this device class has a device_class_init classmethod, run it now
        if hasattr(cls, 'device_class_init'):
            # don't want to use try here in case the called method has an error
            cls.device_class_init(self.machine)

        # create the devices
        for device_name in config:

            if not config[device_name]:
                raise AssertionError("Device '{}' has an empty config."
                                     .format(device_name))

            elif not isinstance(config[device_name], dict):
                raise AssertionError("Device '{}' does not have a valid config."
                                     .format(device_name))

            collection[device_name] = cls(self.machine, device_name)

    def load_devices_config(self, validate=True):
        """Load all devices."""
        if validate:
            for device_type in self.machine.config['mpf']['device_modules']:

                device_cls = Util.string_to_class("mpf.devices." + device_type)

                collection_name, config_name = device_cls.get_config_info()

                if config_name not in self.machine.config:
                    continue

                # Get the config section for these devices
                collection = getattr(self.machine, collection_name)
                config = self.machine.config[config_name]

                # validate config
                for device_name in config:
                    config[device_name] = collection[device_name].prepare_config(config[device_name], False)
                    config[device_name] = collection[device_name].validate_and_parse_config(config[device_name], False)

        for device_type in self.machine.config['mpf']['device_modules']:

            device_cls = Util.string_to_class("mpf.devices." + device_type)

            collection_name, config_name = device_cls.get_config_info()

            if config_name not in self.machine.config:
                continue

            # Get the config section for these devices
            collection = getattr(self.machine, collection_name)
            config = self.machine.config[config_name]

            # load config
            for device_name in config:
                collection[device_name].load_config(config[device_name])

    def initialize_devices(self):
        """Initialise devices."""
        for device_type in self.machine.config['mpf']['device_modules']:

            device_cls = Util.string_to_class("mpf.devices." + device_type)

            collection_name, config_name = device_cls.get_config_info()

            if config_name not in self.machine.config:
                continue

            # Get the config section for these devices
            collection = getattr(self.machine, collection_name)
            config = self.machine.config[config_name]

            # add machine wide
            for device_name in config:
                collection[device_name].device_added_system_wide()

    def get_device_control_events(self, config):
        """Scan a config dictionary for control_events.

         Yields events, methods, delays, and devices for all the devices and control_events in that config.

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
                for device, settings in iter(config[self.collections[collection].config_section].items()):

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
        """Create machine wide control events."""
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
        """Create control events for collection."""
        for collection, events in iter(self.machine.config['mpf']['device_collection_control_events'].items()):

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


class DeviceCollection(CaseInsensitiveDict):

    """A collection of Devices.

    One instance of this class will be created for each different type of
    hardware device (such as coils, lights, switches, ball devices, etc.).
    """

    def __init__(self, machine, collection, config_section):
        """Initialise device collection."""
        super().__init__()

        self.machine = machine
        self.name = collection
        self.config_section = config_section

    def __getattr__(self, attr):
        """Return device by lowercase key."""
        # We use this to allow the programmer to access a hardware item like
        # self.coils.coilname

        try:
            return self[attr.lower()]
        except KeyError:
            raise KeyError('Error: No device exists with the name:', attr)

    def __iter__(self):
        """Iterate collection."""
        for item in self.values():
            yield item

    def __getitem__(self, key):
        """Return device by lowercase key."""
        return super().__getitem__(self.__class__.lower(key))

    def items_tagged(self, tag):
        """Return of list of device objects which have a certain tag.

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
        """Return of list of device names (strings) which have a certain tag.

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
        """Return of list of device objects which do not have a certain tag.

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
        """Check to see if the name passed is a valid device.

        Args:
            name: The string of the device name you want to check.
        Returns:
            True or False, depending on whether the name is a valid device or
            not.
        """
        return name.lower() in iter(self.keys())

    def number(self, number):
        """Return a device object based on its number."""
        for name, obj in self.items():
            if obj.config['number'] == number:
                return self[name]

    def multilist_to_names(self, multilist):
        """Convert list of devices to string list.

        Take a list of strings (including tag strings of device names from this collection, including tags, and returns
        a list of string names.

        Args:
            multilist: List of strings, or a single string separated by commas
                or spaces. Entries can include tag|tagname.

        Returns:
            List of strings of device names. Invalid devices in the input are
            not included in the output.

        The output list will only contain each device once. Order is not
        guaranteed

        Examples:
            input: "led1, led2, tag|playfield"
            return: [led1, led2, led3, led4, led5]

        """
        multilist = self.multilist_to_objects(multilist)
        return [x.name for x in multilist]

    def multilist_to_objects(self, multilist):
        """Same as multilist_to_names() method, except it returns a list of objects instead of a list of strings."""
        multilist = Util.string_to_list(multilist)
        final_list = list()

        for item in multilist:
            objects_from_tags = self.items_tagged(item)
            if objects_from_tags:
                for tagged_object in objects_from_tags:
                    if tagged_object not in final_list:
                        final_list.append(tagged_object)

            else:
                final_list.append(self[item])

        return final_list
