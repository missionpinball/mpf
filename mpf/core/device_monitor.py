"""Decorator to monitor devices."""
from mpf.core.utility_functions import Util


class DeviceMonitor:

    """Monitor variables of a device."""

    def __init__(self, *attributes_to_monitor):
        """Initialise decorator and remember attributes to monitor."""
        self._attributes_to_monitor = attributes_to_monitor

    def __call__(self, cls):
        """Decorate class."""
        _sentinel = object()

        old_init = getattr(cls, '__init__', None)

        def __init__(self_inner, *args, **kwargs):  # noqa
            """Register class at BCP."""
            old_init(self_inner, *args, **kwargs)
            self_inner.machine.bcp.interface.register_monitorable_device(self_inner)

        old_setattr = getattr(cls, '__setattr__', None)

        # pylint: disable-msg=
        def __setattr__(self_inner, name, value):   # noqa
            """If the value changed notify subscribers via BCP."""
            notify = False
            if name in self._attributes_to_monitor:
                old = getattr(self_inner, name, _sentinel)
                if old is not _sentinel and old != value:
                    notify = True
            if old_setattr:
                old_setattr(self_inner, name, value)
            else:
                # Old-style class
                self_inner.__dict__[name] = value

            if notify:
                self_inner.machine.bcp.interface.notify_device_changes(self_inner, name, old, value)

        def get_monitorable_state(self_inner):
            """Return monitorable state of device."""
            state = {}
            for attribute in self._attributes_to_monitor:
                state[attribute] = Util.convert_to_simply_type(getattr(self_inner, attribute))

            return state

        cls.__init__ = __init__
        cls.__setattr__ = __setattr__
        cls.get_monitorable_state = get_monitorable_state

        return cls
