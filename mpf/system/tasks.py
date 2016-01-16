"""Contains the Task, DelayManager, and DelayManagerRegistry base classes."""

import logging
from copy import copy
import time
import uuid


class Task(object):
    """A task/coroutine implementation.

    Tasks are similar to timers except they can yield back to the main loop
    at any point, then be resumed later.

    To wait from a Task, do `yield <ms>`, e.g. `yield 200`.

    To exit from a Task, just return.  This will raise a StopIteration
    exception which the scheduler will catch and remove the task from the
    run queue.
    """

    Tasks = set()
    NewTasks = set()

    def __init__(self, callback, args=None, name=None, sleep=0):
        self.callback = callback
        self.args = args
        self.wakeup = None
        self.name = name
        self.gen = None

        if sleep:
            self.wakeup = time.time() + sleep

    def restart(self):
        """Restarts the task."""
        self.wakeup = None
        self.gen = None

    def stop(self):
        """Stops the task.

        This causes it not to run any longer, by removing it from the task set
        and then deleting it."""
        Task.Tasks.remove(self)

    def __repr__(self):
        return "callback=" + str(self.callback) + " wakeup=" + str(self.wakeup)

    @staticmethod
    def create(callback, args=tuple(), sleep=0):
        """Creates a new task and insert it into the runnable set."""
        task = Task(callback=callback, args=args, sleep=sleep)
        Task.NewTasks.add(task)
        return task

    @staticmethod
    def timer_tick():
        """Scans all tasks now and run those that are ready."""
        dead_tasks = []
        for task in Task.Tasks:
            if not task.wakeup or task.wakeup <= time.time():
                if task.gen:
                    try:
                        rc = next(task.gen)
                        if rc:
                            task.wakeup = time.time() + rc
                    except StopIteration:
                        dead_tasks.append(task)
                else:
                    task.wakeup = time.time()
                    task.gen = task.callback(*task.args)
        for task in dead_tasks:
            Task.Tasks.remove(task)
        # We need to queue the addition to new tasks to the set because if we
        # get a new task while we're iterating above then our set size will
        # change while iterating and produce an error.
        for task in Task.NewTasks:
            Task.Tasks.add(task)
        Task.NewTasks = set()


class DelayManagerRegistry(object):
    def __init__(self):
        self.delay_managers = set()
        self.new_delay_managers = set()

    def add_delay_manager(self, delay_manager):
        self.new_delay_managers.add(delay_manager)

    def get_next_event(self):
        next_event_time = False
        for delay_manager in self.delay_managers:
            next_event_time_single = delay_manager._get_next_event()
            if not next_event_time or (next_event_time > next_event_time_single and next_event_time_single):
                next_event_time = next_event_time_single

        return next_event_time

    def timer_tick(self, machine):
        for i in self.delay_managers:
            i._process_delays(machine)

        while self.new_delay_managers:
            self.delay_managers.add(self.new_delay_managers.pop())


class DelayManager(object):
    """Handles delays for one object"""

    def __init__(self, registry):
        self.log = logging.getLogger("DelayManager")
        self.delays = {}
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
        self.delays[name] = ({'action_ms': time.time() + (ms / 1000.0),
                              'callback': callback,
                              'kwargs': kwargs})

        return name

    def remove(self, name):
        """Removes a delay. (i.e. prevents the callback from being fired and
        cancels the delay.)

        Args:
            name: String name of the delay you want to remove. If there is no
                delay with this name, that's ok. Nothing happens.
        """

        self.log.debug("Removing delay: '%s'", name)
        try:
            del self.delays[name]
        except:
            pass

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
        self.remove(name)
        self.add(ms, callback, name, **kwargs)

    def clear(self):
        """Removes (clears) all the delays associated with this DelayManager."""
        self.delays = {}

    def _get_next_event(self):
        next_event_time = False
        for delay in list(self.delays.keys()):
            if not next_event_time or next_event_time > self.delays[delay]['action_ms']:
                next_event_time = self.delays[delay]['action_ms']

        return next_event_time

    def _process_delays(self, machine):
        # Processes any delays that should fire now
        for delay in list(self.delays.keys()):
            # previous delay may have deleted it
            if not delay in self.delays:
                continue
            if self.delays[delay]['action_ms'] <= time.time():
                # Delete the delay first in case the processing of it adds a
                # new delay with the same name. If we delete as the final step
                # then we'll inadvertantly delete the newly-set delay
                this_delay = copy(self.delays[delay])
                del self.delays[delay]
                self.log.debug("---Processing delay: %s", this_delay)
                if this_delay['kwargs']:
                    this_delay['callback'](**this_delay['kwargs'])
                else:
                    this_delay['callback']()

            # Process event queue after delay
            machine.events._process_event_queue()



