# tasks.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from copy import copy
import time


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
    def Create(callback, args=tuple(), sleep=0):
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


class DelayManager(object):
    """Parent class for a delay manager which can manage multiple delays."""

    delay_managers = set()
    dead_delay_managers = set()

    # todo it might not make sense to keep each DelayManager as a separate
    # class instance. It makes iterating complex and doesn't really add any
    # value? (Well, apart from it's easy to wipe all the delays that a single
    # module created.) But it might be faster to just have a single delay
    # manager for the whole system. Then again, we're only iterating at a
    # relatively slow loop rate.

    def __init__(self):
        self.log = logging.getLogger("DelayManager")
        self.delays = {}
        DelayManager.delay_managers.add(self)

    def __del__(self):
        DelayManager.dead_delay_managers.add(self)  # todo I don't like this

    def add(self, name, ms, callback, **kwargs):
        """Adds a delay.

        Args:
            name: String name of this delay. This name is arbitrary and only
                used to identify the delay later if you want to remove or change
                it.
            ms: Int of the number of milliseconds you want this delay to be for.
                Note that the resolution of this time is based on your
                machine's tick rate. The callback will be called on the
                first machine tick *after* the delay time has expired. For
                example, if you have a machine tick rate of 30Hz, that's 33.33ms
                per tick. So if you set a delay for 40ms, the actual delay will
                be 66.66ms since that's the next tick time after the delay ends.
            callback: The method that is called when this delay ends.
            **kwargs: Any other (optional) kwarg pairs you pass will be
                passed along as kwargs to the callback method.
        """
        self.log.debug("Adding delay. Name: '%s' ms: %s, callback: %s, "
                       "kwargs: %s", name, ms, callback, kwargs)
        self.delays[name] = ({'action_ms': time.time() + (ms / 1000.0),
                              'callback': callback,
                              'kwargs': kwargs})

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
        self.add(name, ms, callback, **kwargs)

    def clear(self):
        """Removes (clears) all the delays associated with this DelayManager."""
        self.delays = {}

    def _process_delays(self):
        # Processes any delays that should fire now
        for delay in self.delays.keys():
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

    @staticmethod
    def timer_tick():
        # This is kind of complex because we have to account for a delay
        # manager being deleted while we're iterating.
        live_delay_managers = set()
        while DelayManager.delay_managers:
            i = DelayManager.delay_managers.pop()
            if i not in DelayManager.dead_delay_managers:
                i._process_delays()
                live_delay_managers.add(i)
        DelayManager.delay_managers = live_delay_managers

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
