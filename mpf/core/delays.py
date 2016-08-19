"""Manages delays within a context."""

import logging
import uuid
from functools import partial


class DelayManagerRegistry(object):

    """Keeps references to all DelayManager instances."""

    def __init__(self, machine):
        """Initialise delay registry."""
        self.delay_managers = set()
        self.machine = machine

    def add_delay_manager(self, delay_manager):
        """Add a delay manager to the list."""
        self.delay_managers.add(delay_manager)


class DelayManager(object):

    """Handles delays for one object."""

    def __init__(self, registry):
        """Initialise delay manager."""
        self.log = logging.getLogger("DelayManager")
        self.delays = {}
        self.machine = registry.machine
        self.registry = registry
        self.registry.add_delay_manager(self)

    def add(self, ms, callback, name=None, **kwargs):
        """Add a delay.

        Args:
            ms: Int of the number of milliseconds you want this delay to be for.
                Note that the resolution of this time is based on your
                machine's tick rate. The callback will be called on the
                first machine tick *after* the delay time has expired. For
                example, if you have a machine tick rate of 30Hz, that's 33.33ms
                per tick. So if you set a delay for 40ms, the actual delay will
                be 66.66ms since that's the next tick time after the delay ends.
            callback: The method that is called when this delay ends.
            name: String name of this delay. This name is arbitrary and only
                used to identify the delay later if you want to remove or change
                it. If you don't provide it, a UUID4 name will be created.
            **kwargs: Any other (optional) kwarg pairs you pass will be
                passed along as kwargs to the callback method.

        Returns:
            String name of the delay which you can use to remove it later.
        """
        if not name:
            name = uuid.uuid4()
        self.log.debug("Adding delay. Name: '%s' ms: %s, callback: %s, "
                       "kwargs: %s", name, ms, callback, kwargs)

        if name in self.delays:
            self.machine.clock.unschedule(self.delays[name])
            del self.delays[name]

        self.delays[name] = self.machine.clock.schedule_once(
            partial(self._process_delay_callback, name, callback, **kwargs),
            ms / 1000.0)

        return name

    def remove(self, name):
        """Remove a delay by name.

        I.e. prevents the callback from being fired and cancels the delay.

        Args:
            name: String name of the delay you want to remove. If there is no
                delay with this name, that's ok. Nothing happens.
        """
        self.log.debug("Removing delay: '%s'", name)
        if name in self.delays:
            self.machine.clock.unschedule(self.delays[name])
            try:
                del self.delays[name]
            except KeyError:
                pass

    def check(self, delay):
        """Check to see if a delay exists.

        Args:
            delay: A string of the delay you're checking for.

        Returns: The delay object if it exists, or None if not.
        """
        if delay in self.delays:
            return delay

    def reset(self, name, ms, callback, **kwargs):
        """Reset a delay, first deleting the old one (if it exists) and then adding new delay with the new settings.

        Args:
            same as add()
        """
        if name in self.delays:
            self.remove(name)

        self.add(ms, callback, name, **kwargs)

    def clear(self):
        """Remove (clear) all the delays associated with this DelayManager."""
        for name in list(self.delays.keys()):
            self.machine.clock.unschedule(self.delays[name])
            self.remove(name)

        self.delays = {}

    def _process_delay_callback(self, name, callback, dt, **kwargs):
        del dt
        self.log.debug("---Processing delay: %s", name)
        try:
            del self.delays[name]
        except KeyError:
            pass
        callback(**kwargs)
        self.machine.events.process_event_queue()
