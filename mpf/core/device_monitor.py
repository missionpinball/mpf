"""Decorator to monitor devices."""
from mpf.core.utility_functions import Util


class DeviceMonitor:

    """Monitor variables of a device."""

    def __init__(self, *attributes_to_monitor, **aliased_attributes_to_monitor):
        """Initialise decorator and remember attributes to monitor."""
        self._attributes_to_monitor = attributes_to_monitor
        self._aliased_attributes_to_monitor = aliased_attributes_to_monitor

    def __call__(self, cls):
        """Decorate class."""
        _sentinel = object()

        old_init = getattr(cls, '__init__', None)

        def __init__(self_inner, *args, **kwargs):  # noqa
            """Register class."""
            old_init(self_inner, *args, **kwargs)
            self_inner.machine.device_manager.register_monitorable_device(self_inner)

        old_setattr = getattr(cls, '__setattr__', None)

        # pylint: disable-msg=
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
                self_inner.machine.device_manager.notify_device_changes(self_inner, attribute_name, old, value)

        def get_monitorable_state(self_inner):
            """Return monitorable state of device."""
            state = {}
            for attribute in self._attributes_to_monitor:
                state[attribute] = Util.convert_to_simply_type(getattr(self_inner, attribute))

            for attribute, name in self._aliased_attributes_to_monitor.items():
                state[name] = Util.convert_to_simply_type(getattr(self_inner, attribute))

            return state

        cls.__init__ = __init__
        cls.__setattr__ = __setattr__
        cls.get_monitorable_state = get_monitorable_state

        return cls
