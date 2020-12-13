"""Decorator to monitor devices."""
import asyncio
from collections import defaultdict

from mpf.core.utility_functions import Util


class DeviceMonitor:

    """Monitor variables of a device."""

    __slots__ = ["_attributes_to_monitor", "_aliased_attributes_to_monitor", "_do_not_overwrite_setter"]

    def __init__(self, *attributes_to_monitor, _do_not_overwrite_setter=False, **aliased_attributes_to_monitor):
        """Initialise decorator and remember attributes to monitor."""
        self._attributes_to_monitor = attributes_to_monitor
        self._aliased_attributes_to_monitor = aliased_attributes_to_monitor
        self._do_not_overwrite_setter = _do_not_overwrite_setter

    def __call__(self, cls):    # noqa
        """Decorate class."""
        _sentinel = object()

        old_init = getattr(cls, '__init__', None)

        def __init__(self_inner, *args, **kwargs):  # noqa
            """Register class."""
            old_init(self_inner, *args, **kwargs)
            self_inner.machine.device_manager.register_monitorable_device(self_inner)

        old_setattr = getattr(cls, '__setattr__', None)
        super_get_placeholder_value = getattr(cls, "get_placeholder_value", None)

        def __setattr__(self_inner, name, value):   # noqa
            """If the value changed notify subscribers."""
            attribute_name = False
            if name in self._attributes_to_monitor:
                old = getattr(self_inner, name, _sentinel)
                if old is not _sentinel and old != value:
                    attribute_name = name
            elif name in self._aliased_attributes_to_monitor:
                old = getattr(self_inner, name, _sentinel)
                if old is not _sentinel and old != value:
                    attribute_name = self._aliased_attributes_to_monitor[name]

            if old_setattr:
                old_setattr(self_inner, name, value)
            else:
                # Old-style class
                self_inner.__dict__[name] = value

            if attribute_name:
                _notify_placeholder_change(self_inner, attribute_name, old, value)

        def _notify_placeholder_change(self_inner, attribute_name, old, value):
            if old != value:
                self_inner.machine.device_manager.notify_device_changes(self_inner, attribute_name, old, value)
                for future in cls.attribute_futures[self_inner][attribute_name]:
                    if not future.done():
                        future.set_result(True)
                cls.attribute_futures[self_inner][attribute_name] = []

        def get_monitorable_state(self_inner):
            """Return monitorable state of device."""
            state = {}
            for attribute in self._attributes_to_monitor:
                state[attribute] = Util.convert_to_simply_type(getattr(self_inner, attribute))

            for attribute, name in self._aliased_attributes_to_monitor.items():
                state[name] = Util.convert_to_simply_type(getattr(self_inner, attribute))

            return state

        def subscribe_attribute(self_inner, item, machine):
            """Subscribe to an attribute."""
            del machine
            future = asyncio.Future()
            cls.attribute_futures[self_inner][item].append(future)
            return future

        def get_placeholder_value(self_inner, item):
            """Get the value of a placeholder."""
            if item in self._attributes_to_monitor:
                return Util.convert_to_simply_type(getattr(self_inner, item))

            for attribute, name in self._aliased_attributes_to_monitor.items():
                if name == item:
                    return Util.convert_to_simply_type(getattr(self_inner, attribute))

            if super_get_placeholder_value:
                return super_get_placeholder_value(self_inner, item)

            raise ValueError("Attribute {} does not exist.".format(item))

        cls.__init__ = __init__
        if not self._do_not_overwrite_setter:
            cls.__setattr__ = __setattr__
        cls.get_monitorable_state = get_monitorable_state
        cls.get_placeholder_value = get_placeholder_value
        cls.subscribe_attribute = subscribe_attribute
        cls.notify_virtual_change = _notify_placeholder_change
        cls.attribute_futures = defaultdict(lambda: defaultdict(list))

        return cls
