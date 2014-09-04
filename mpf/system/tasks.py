# tasks.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.timing import Timing
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
        """Initialization of a task.

        The task is defined by a callable function and a list of arguments,
        which denotes how the task is first called.
        """
        self.callback = callback
        self.args = args
        self.wakeup = None
        self.name = name
        self.gen = None

        if sleep:
            self.wakeup = time.time() + sleep

    def restart(self):
        """Restart a task."""
        self.wakeup = None
        self.gen = None

    def stop(self):
        """Stop a task.

        This causes it not to run any longer, by removing it from the task set
        and then deleting it."""
        Task.Tasks.remove(self)

    def __str__(self):
        return "callback=" + str(self.callback) + " wakeup=" + str(self.wakeup)

    @staticmethod
    def Create(callback, args=tuple(), sleep=0):
        """Create a new task and insert it into the runnable set."""
        task = Task(callback=callback, args=args, sleep=sleep)
        Task.NewTasks.add(task)
        return task

    @staticmethod
    def timer_tick():
        """Scan all tasks now and run those that are ready.

        'now' is the tick number, not a time.time(). Just FYI
        """
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

    def add(self, name, ms, callback, args=None):
        """ delay comes in via ms.
        """
        self.log.debug("---Adding delay. Name: '%s' ms: %s, callback: %s, args: %s",
                       name, ms, callback, args)
        self.delays[name] = ({'action_ms': time.time() + (ms / 1000.0),
                              'callback': callback,
                              'args': args})

    def remove(self, name):
        self.log.debug("---Removing delay: '%s'", name)
        try:
            del self.delays[name]
        except:
            pass

    def reset(self, name, ms, callback, args=None):
        """ Resets a delay, first deleting the old one (if it exists) and then
        adding the delay for the new time.
        """
        self.remove(name)
        self.add(name, ms, callback, args)

    def clear(self):
        self.delays = {}

    def process_delays(self):
        """ Processes any delays that should fire now """
        for delay in self.delays.keys():
            if self.delays[delay]['action_ms'] <= time.time():
                # Delete the delay first in case the processing of it adds a
                # new delay with the same name. If we delete as the final step
                # then we'll inadvertantly delete the newly-set delay
                this_delay = copy(self.delays[delay])
                del self.delays[delay]
                self.log.debug("---Processing delay: %s", this_delay)
                if this_delay['args']:
                    this_delay['callback'](this_delay['args'])
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
                i.process_delays()
                live_delay_managers.add(i)
        DelayManager.delay_managers = live_delay_managers

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
