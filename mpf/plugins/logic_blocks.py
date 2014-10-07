"""MPF plugin which implements Logic Blocks"""

# logic_blocks.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging

from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing


def preload_check(machine):
    return True


class LogicBlocks(object):
    """LogicBlock Manager."""

    def __init__(self, machine):
        self.machine = machine
        self.logic_blocks = set()

        if self.machine.config['LogicBlocks']:

            if 'HitCounters' in self.machine.config['LogicBlocks']:
                for item in self.machine.config['LogicBlocks']['HitCounters']:
                    block = HitCounter(self.machine, item,
                                       self.machine.config['LogicBlocks']
                                       ['HitCounters'][item])
                    self.logic_blocks.add(block)

            if 'Accruals' in self.machine.config['LogicBlocks']:
                for item in self.machine.config['LogicBlocks']['Accruals']:
                    block = Accrual(self.machine, item,
                                       self.machine.config['LogicBlocks']
                                       ['Accruals'][item])
                    self.logic_blocks.add(block)
            if 'Sequences' in self.machine.config['LogicBlocks']:
                for item in self.machine.config['LogicBlocks']['Sequences']:
                    block = Sequence(self.machine, item,
                                       self.machine.config['Sequences']
                                       ['Accruals'][item])
                    self.logic_blocks.add(block)


class LogicBlock(object):
    """Parent class for each of the logic block classes."""

    def __init__(self, machine, name, config):
        self.machine = machine
        self.name = name
        self.config = config

        self.enabled = False

        if 'enable_events' not in self.config:
            self.config['enable_events'] = [None]
        else:
            self.config['enable_events'] = self.machine.string_to_list(
                self.config['enable_events'])

        if 'disable_events' not in self.config:
            self.config['disable_events'] = [None]
        else:
            self.config['disable_events'] = self.machine.string_to_list(
                self.config['disable_events'])

        if 'reset_events' not in self.config:
            self.config['reset_events'] = [None]
        else:
            self.config['reset_events'] = self.machine.string_to_list(
                self.config['reset_events'])

        if 'events_when_complete' not in self.config:
            self.config['events_when_complete'] = ([
                'eventtrigger_' + self.name + '_complete'])
        else:
            self.config['events_when_complete'] = self.machine.string_to_list(
                self.config['events_when_complete'])

        if 'restart_on_complete' not in self.config:
            self.config['restart_on_complete'] = False

        # register for events

        for event in self.config['enable_events']:
            self.machine.events.add_handler(event, self.enable)
        for event in self.config['disable_events']:
            self.machine.events.add_handler(event, self.disable)
        for event in self.config['reset_events']:
            self.machine.events.add_handler(event, self.reset)

    def enable(self, **kwargs):
        """Enables this logic block. Automatically called when one of the
        enable_event events is posted. Can also manually be called.
        """
        self.log.debug("Enabling")
        self.enabled = True

    def disable(self, **kwargs):
        """Disables this logic block. Automatically called when one of the
        disable_event events is posted. Can also manually be called.
        """
        self.log.debug("Disabling")
        self.enabled = False
        self.machine.events.remove_handler(self.hit)

    def reset(self, **kwargs):
        """Resets the progress towards completion of this logic block.
        Automatically called when one of the reset_event events is called.
        Can also be manually called.
        """
        self.log.debug("Resetting")

    def complete(self):
        self.log.debug("Complete")
        if self.config['events_when_complete']:
            for event in self.config['events_when_complete']:
                self.machine.events.post(event)

        if self.config['restart_on_complete']:
            self.reset()
            self.enable()
        else:
            self.disable()


class HitCounter(LogicBlock):
    """A type of LogicBlock that tracks multiple hits of a single event.

    Supports counting closely-spaced hits as one hit. This type of LogicBlock is
    used for things like counting the tilt hits.
    """

    # todo settle time

    def __init__(self, machine, name, config):
        self.log = logging.getLogger('HitCounter.' + name)
        self.log.debug("Creating HitCounter LogicBlock")

        super(HitCounter, self).__init__(machine, name, config)

        self.delay = DelayManager()

        self.num_hits = 0
        self.ignore_hits = False

        if 'trigger_events' not in self.config:
            return  # Not much point to continue here
        else:
            self.config['trigger_events'] = self.machine.string_to_list(
                self.config['trigger_events'])

        if 'event_when_hit' not in self.config:
            self.config['event_when_hit'] = ('eventtrigger_' + self.name +
                                             '_hit')

        if 'hits_to_complete' not in self.config:
            self.config['hits_to_complete'] = 1

        if 'multiple_hit_window' not in self.config:
            self.config['multiple_hit_window'] = None
        else:
            self.config['multiple_hit_window'] = Timing.string_to_ms(
                self.config['multiple_hit_window'])
        if 'settle_time' not in self.config:
            self.config['settle_time'] = None
        else:
            self.config['settle_time'] = Timing.string_to_ms(
                self.config['settle_time'])

    def enable(self, **kwargs):
        """Enables this trigger. Automatically called when one of the
        'enable_event's is posted. Can also manually be called.
        """
        super(HitCounter, self).enable(**kwargs)
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        self.enabled = True

        for event in self.config['trigger_events']:
            self.machine.events.add_handler(event, self.hit)

    def reset(self, **kwargs):
        """Resets the hit progress towards completion"""
        super(HitCounter, self).reset(**kwargs)
        self.num_hits = 0

    def hit(self, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the `trigger_events`s is posted. Can also manually be
        called.
        """
        if not self.ignore_hits:
            self.num_hits += 1
            self.log.debug("Processing Hit. Total: %s", self.num_hits)

            if self.num_hits >= self.config['hits_to_complete']:
                self.complete()

            if self.config['event_when_hit']:
                self.machine.events.post(self.config['event_when_hit'],
                                         hits=self.num_hits)

            if self.config['multiple_hit_window']:
                self.log.debug("Beginning Ignore Hits")
                self.ignore_hits = True
                self.delay.add('ignore_hits_within_window',
                               self.config['multiple_hit_window'],
                               self.stop_ignoring_hits)

    def stop_ignoring_hits(self, **kwargs):
        """Causes the EventTrigger to stop ignoring subsequent hits that occur
        within the 'multiple_hit_window'. Automatically called when the window
        time expires. Can safely be manually called.
        """
        self.log.debug("Ending Ignore hits")
        self.ignore_hits = False


class Accrual(LogicBlock):
    """A type of LogicBlock which tracks many different events (steps) towards
    a goal, with the steps being able to happen in any order.
    """

    def __init__(self, machine, name, config):
        self.log = logging.getLogger('Accrual.' + name)
        self.log.debug("Creating Accrual LogicBlock")

        super(Accrual, self).__init__(machine, name, config)

        self.status = list()

        # make sure the events entry is a list of lists
        if 'events' in self.config and type(self.config['events']) is list:
            for entry_num in range(len(self.config['events'])):
                self.config['events'][entry_num] = (
                    self.machine.string_to_list(self.config['events']
                                                [entry_num]))
        elif 'events' in self.config and type(self.config['events']) is str:
            temp_list = self.machine.string_to_list(self.config['events'])
            self.config['events'] = list()
            for entry_num in temp_list:
                self.config['events'].append([entry_num])

        # populate our status list
        self.status = [False] * len(self.config['events'])

    def enable(self, **kwargs):
        """Enables this accrual. Automatically called when one of the
        'enable_event's is posted. Can also manually be called.
        """
        super(Accrual, self).enable(**kwargs)
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        for entry_num in range(len(self.config['events'])):
            for event in self.config['events'][entry_num]:
                self.machine.events.add_handler(event, self.hit,
                                                step=entry_num)

    def reset(self, **kwargs):
        """Resets the hit progress towards completion"""
        super(Accrual, self).reset(**kwargs)

        self.status = [False] * len(self.config['events'])
        self.log.debug("Status: %s", self.status)

    def hit(self, step, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the `trigger_events`s is posted. Can also manually be
        called.
        """
        self.log.debug("Processing hit for step: %s", step)
        self.status[step] = True
        self.log.debug("Status: %s", self.status)

        if self.status.count(True) == len(self.status):
            self.complete()


class Sequence(LogicBlock):
    """A type of LogicBlock which tracks many different events (steps) towards
    a goal, with the steps having to happen in order.
    """

    def __init__(self, machine, name, config):
        self.log = logging.getLogger('Sequence.' + name)
        self.log.debug("Creating Sequence LogicBlock")

        super(Sequence, self).__init__(machine, name, config)

        self.current_step = 1

        # make sure the events entry is a list of lists
        if 'events' in self.config and type(self.config['events']) is list:
            for entry_num in range(len(self.config['events'])):
                self.config['events'][entry_num] = (
                    self.machine.string_to_list(self.config['events']
                                                [entry_num]))

    def enable(self, step=0, **kwargs):
        """Enables this Sequence. Automatically called when one of the
        'enable_event's is posted. Can also manually be called.
        """
        self.log.debug("Enabling")
        if step:
            self.current_step = step

        if self.current_step >= len(self.config['events']):
            # hmm.. we're enabling, but we're done. So now what?
            self.log.warning("Received request to enable at step %s, but this "
                             " Sequence only has %s step(s). Marking complete",
                             step, len(self.config['events']))
            self.complete()  # I guess we just complete?
            return

        self.enabled = True
        # add the handlers for the current step
        for event in self.config['events'][self.current_step]:
            self.machine.events.add_handler(event, self.hit)

    def hit(self, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the `trigger_events`s is posted. Can also manually be
        called.
        """
        self.log.debug("Processing Hit")
        # remove the event handlers for this step
        self.machine.events.remove_handler(self.hit)

        self.current_step += 1

        if self.current_step >= len(self.config['events']):
            self.complete()
        else:
            # add the handlers for the new current step
            for event in self.config['events'][self.current_step]:
                self.machine.events.add_handler(event, self.hit)

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
