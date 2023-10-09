"""Contains the DeviceManager base class."""
import asyncio

from typing import Callable, Tuple, List, Generator, Dict

from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.device import Device  # pylint: disable-msg=cyclic-import,unused-import


class DeviceManager(MpfController):

    """Manages all the devices in MPF."""

    config_name = "device_manager"

    __slots__ = ["_monitorable_devices", "collections", "_device_classes"]

    def __init__(self, machine):
        """Initialize device manager."""
        super().__init__(machine)

        self._monitorable_devices = {}

        self.collections = dict()
        self._device_classes = {}           # type: Dict[str, Device]

        # this has to happen after mode load
        self.machine.events.add_async_handler('init_phase_1',
                                              self._load_device_modules, priority=5)

        self.machine.events.add_handler('init_phase_2',
                                        self.create_machinewide_device_control_events,
                                        priority=2)

    def get_monitorable_devices(self):
        """Return all devices which are registered as monitorable."""
        return self._monitorable_devices

    def register_monitorable_device(self, device):
        """Register a monitorable device.

        Args:
        ----
            device: The device to register.
        """
        if device.collection not in self._monitorable_devices:
            self._monitorable_devices[device.collection] = {}
        self._monitorable_devices[device.collection][device.name] = device

    def notify_device_changes(self, device, notify, old, value):
        """Notify subscribers about changes in a registered device.

        Args:
        ----
            device: The device that changed.
            notify: Attribute name which changed.
            old: The old value.
            value: The new value.

        """
        self.machine.bcp.interface.notify_device_changes(device, notify, old, value)

    async def _load_device_modules(self, **kwargs):
        del kwargs
        # step 1: create devices in machine collection
        self.debug_log("Creating devices...")
        for collection_name in self.machine.config['mpf']['device_modules'].keys():
            # create the collection
            collection = DeviceCollection(self.machine, collection_name, collection_name)

            self.collections[collection_name] = collection
            setattr(self.machine, collection_name, collection)

            # Get the config section for these devices
            config = self.machine.config.get(collection_name, None)

            # create the devices
            if config:
                self.create_devices(collection_name, config)

        self.machine.mode_controller.create_mode_devices()

        # step 2: load config and validate devices
        self.load_devices_config(validate=True)
        await self.machine.mode_controller.load_mode_devices()

        # step 3: initialize devices (mode devices will be initialized when mode is started)
        await self.initialize_devices()

    def stop_devices(self):
        """Stop all devices in the machine."""
        for collection in self.collections.values():
            for device in collection.values():
                if hasattr(device, "stop_device"):
                    device.stop_device()

    def create_devices(self, collection_name, config):
        """Create devices for a collection."""
        if collection_name not in self._device_classes:
            cls = self._device_classes[collection_name] = Util.string_to_class(
                self.machine.config['mpf']['device_modules'][collection_name])
        else:
            cls = self._device_classes[collection_name]

        collection = getattr(self.machine, collection_name)

        # if this device class has a device_class_init classmethod, run it now
        if hasattr(cls, 'device_class_init'):
            # don't want to use try here in case the called method has an error
            cls.device_class_init(self.machine)

        # create the devices
        for device_name in config:
            if not config[device_name] and not cls.allow_empty_configs:
                self.raise_config_error("Device {}:'{}' has an empty config.".format(collection_name, device_name), 2,
                                        context=collection_name + "." + device_name)

            elif not isinstance(config[device_name], dict):
                self.raise_config_error("Device {}:'{}' does not have a valid config. Expected a dictionary.".format(
                    collection_name, device_name), 3, context=collection_name + "." + device_name)

            collection[device_name] = cls(self.machine, device_name)

    def load_devices_config(self, validate=True):
        """Load all devices."""
        if validate:
            for collection_name in self.machine.config['mpf']['device_modules'].keys():
                if collection_name not in self.machine.config:
                    continue

                # Get the config section for these devices
                collection = getattr(self.machine, collection_name)
                config = self.machine.config[collection_name]
                if not config:
                    self.machine.config[collection_name] = config = {}
                if not isinstance(config, dict):
                    self.raise_config_error("Format of collection {} is invalid.".format(collection_name), 1)

                # validate config
                for device_name in config:
                    config[device_name] = collection[device_name].prepare_config(config[device_name], False)
                    config[device_name] = collection[device_name].validate_and_parse_config(config[device_name], False)

        for collection_name in self.machine.config['mpf']['device_modules'].keys():
            if collection_name not in self.machine.config:
                continue

            # Get the config section for these devices
            collection = getattr(self.machine, collection_name)
            config = self.machine.config[collection_name]

            # load config
            for device_name in config:
                collection[device_name].load_config(config[device_name])

    async def initialize_devices(self):
        """initialize devices."""
        futures = []
        for collection_name in self.machine.config['mpf']['device_modules'].keys():
            if collection_name not in self.machine.config:
                continue

            # Get the config section for these devices
            collection = getattr(self.machine, collection_name)
            config = self.machine.config[collection_name]

            # add machine wide
            for device_name in config:
                futures.append(collection[device_name].device_added_system_wide())

        await asyncio.wait([asyncio.create_task(futures) for futures in futures])

    # pylint: disable-msg=too-many-nested-blocks
    def get_device_control_events(self, config) -> Generator[Tuple[str, Callable, int, "Device"], None, None]:
        """Scan a config dictionary for control_events.

         Yields events, methods, delays, and devices for all the devices and
         control_events in that config.

        Args:
        ----
            config: An MPF config dictionary (either machine-wide or mode-
                specific).

        Returns a generator of 4-item tuples
        ------------------------------------
            * The event name
            * The callback method of the device
            * The delay in ms
            * The device object
        """
        config_spec = self.machine.config_validator.get_config_spec()
        for collection in self.collections:
            config_section = self.collections[collection].config_section
            if config_section in config:
                for device, settings in iter(config[config_section].items()):

                    control_events = [x for x in settings if
                                      x.endswith('_events') and x != "control_events"]
                    device_obj = self.collections[collection][device]

                    for control_event in control_events:
                        # get events from this device's config
                        if not isinstance(settings[control_event], dict):
                            if config_spec[config_section][control_event] == "ignore":
                                continue
                            raise AssertionError(
                                "Type of {}:{} should be event_handler|event_handler:ms| in config_spec".format(
                                    collection, control_event))
                        # try the new style first
                        try:
                            method = getattr(device_obj, "event_{}".format(control_event[:-7]))
                        except AttributeError:
                            raise AssertionError("Class {} needs to have method event_{} to handle {}".format(
                                device_obj, control_event[:-7], control_event
                            ))
                        for event, delay in settings[control_event].items():
                            yield (event,
                                   method,
                                   delay,
                                   device_obj)

    def create_machinewide_device_control_events(self, **kwargs):
        """Create machine wide control events."""
        del kwargs
        for event, method, delay, _ in (
                self.get_device_control_events(self.machine.config)):

            if delay:
                self.machine.events.add_handler(
                    event=event,
                    handler=self._control_event_handler,
                    callback=method,
                    ms_delay=delay,
                    delay_mgr=self.machine.delay)
            else:
                self.machine.events.add_handler(
                    event=event,
                    handler=method)

    def _control_event_handler(self, callback, ms_delay, delay_mgr=None, **kwargs):
        del kwargs

        self.debug_log("_control_event_handler: callback: %s,", callback)
        delay_mgr.add(ms=ms_delay, callback=callback)


class DeviceCollection(dict):

    """A collection of Devices.

    One instance of this class will be created for each different type of
    hardware device (such as coils, lights, switches, ball devices, etc.).
    """

    __slots__ = ["machine", "name", "config_section", "_tag_cache"]

    def __init__(self, machine, collection, config_section):
        """initialize device collection."""
        super().__init__()

        self.machine = machine
        self.name = collection
        self.config_section = config_section
        self._tag_cache = dict()

    def __hash__(self):
        """Hash collection."""
        return hash((self.name, self.machine))

    def __delitem__(self, key):
        """Delete item for key."""
        # clear the tag cache
        self._tag_cache = dict()
        return super().__delitem__(key)

    def __getattr__(self, attr):
        """Return device by key.

        This method is DEPRECATED and will be removed soon.
        """
        # We used this to allow the programmer to access a hardware item like
        # self.coils.coilname

        try:
            return self[attr]
        except KeyError:
            raise KeyError('Error: No device exists with the name:', attr)

    def __iter__(self):
        """Iterate collection.

        This method is DEPRECATED and will be removed soon. Use .values() instead.
        """
        for item in self.values():
            yield item

    def items_tagged(self, tag) -> List["Device"]:
        """Return of list of device objects which have a certain tag.

        Args:
        ----
            tag: A string of the tag name which specifies what devices are
                returned.  A value of "*" returns all devices.

        Returns a list of device objects. If no devices are found with that tag, it
        will return an empty list.
        """
        if tag == "*":
            return self.values()

        items_in_tag_cache = self._tag_cache.get(tag, None)
        if items_in_tag_cache is not None:
            return items_in_tag_cache

        items = [item for item in self.values() if hasattr(item, "tags") and tag in item.tags]
        self._tag_cache[tag] = items
        return items
