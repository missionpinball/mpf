"""Contains the Task, DelayManager, and DelayManagerRegistry base classes."""

import logging
import uuid
from functools import partial


class Task(object):
    """A task/coroutine implementation.

    Tasks are similar to timers except they can yield back to the main loop
    at any point, then be resumed later.

    To wait from a Task, do `yield <ms>`, e.g. `yield 200`.

    To exit from a Task, just return.  This will raise a StopIteration
    exception which the scheduler will catch and remove the task from the
    run queue.
    """

    def __init__(self, machine, callback, args=None, name=None, interval=0, delay=0):
        self.machine = machine
        self.callback = callback
        self.args = args
        self.name = name
        self.interval = interval
        self.delay = delay
        self.clock_event = None

        if delay:
            self.clock_event = self.machine.clock.schedule_once(self.run, delay)
        else:
            self.run(0)

    def __del__(self):
        self.stop()

    @property
    def running(self):
        return self.clock_event is not None

    def run(self, dt):
        self.stop()
        self.clock_event = self.machine.clock.schedule_interval(self._process_task, self.interval)

    def _process_task(self, dt):
        if self.callback is not None:
            self.callback(*self.args)

    def stop(self):
        """Stops the task. This causes it not to run any longer"""
        if self.clock_event:
            self.machine.clock.unschedule(self.clock_event)
            self.clock_event = None

    def __repr__(self):
        return "callback=" + str(self.callback) + " interval=" + str(self.interval) + " delay=" + str(self.delay)

    @staticmethod
    def create(machine, callback, args=tuple(), interval=0, delay=0):
        """Creates a new task and insert it into the runnable set."""
        return Task(machine=machine, callback=callback, args=args, interval=interval, delay=delay)


class DelayManagerRegistry(object):
    def __init__(self, machine):
        self.delay_managers = set()
        self.machine = machine

    def add_delay_manager(self, delay_manager):
        self.delay_managers.add(delay_manager)

    def get_next_event(self):
        next_event_time = False
        for delay_manager in self.delay_managers:
            next_event_time_single = delay_manager._get_next_event()
            if not next_event_time or (next_event_time > next_event_time_single and next_event_time_single):
                next_event_time = next_event_time_single

        return next_event_time


class DelayManager(object):
    """Handles delays for one object"""

    def __init__(self, registry):
        self.log = logging.getLogger("DelayManager")
        self.delays = {}
        self.machine = registry.machine
        self.registry = registry
        self.registry.add_delay_manager(self)

    def add(self, ms, callback, name=None, **kwargs):
        """Adds a delay.

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
        """Removes a delay. (i.e. prevents the callback from being fired and
        cancels the delay.)

        Args:
            name: String name of the delay you want to remove. If there is no
                delay with this name, that's ok. Nothing happens.
        """

        self.log.debug("Removing delay: '%s'", name)
        if name in self.delays:
            self.machine.clock.unschedule(self.delays[name])
            del self.delays[name]

    def check(self, delay):
        """Checks to see if a delay exists.

        Args:
            delay: A string of the delay you're checking for.

        Returns: The delay object if it exists, or None if not.
        """
        if delay in self.delays:
            return delay

    def reset(self, name, ms, callback, **kwargs):
        """Resets a delay, first deleting the old one (if it exists) and then
        adding new delay with the new settings.

        Args:
            same as add()
        """
        if name in self.delays:
            self.remove(name)

        self.add(ms, callback, name, **kwargs)

    def clear(self):
        """Removes (clears) all the delays associated with this DelayManager."""
        for name in list(self.delays.keys()):
            self.machine.clock.unschedule(self.delays[name])
            self.remove(name)

        self.delays = {}

    def _get_next_event(self):
        next_event_time = False
        for name in list(self.delays.keys()):
            if not next_event_time or next_event_time > self.delays[name].next_event_time:
                next_event_time = self.delays[name].next_event_time

        return next_event_time

    def _process_delay_callback(self, name, callback, dt, **kwargs):
        self.log.debug("---Processing delay: %s", name)
        del self.delays[name]
        callback(**kwargs)
