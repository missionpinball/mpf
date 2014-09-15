"""Contains the EventTrigger and EventTriggers parent classes."""

# event_triggers.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging

from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing


class EventTriggers(object):
    def __init__(self, machine):
        self.machine = machine
        self.config = self.machine.config['EventTriggers']
        self.event_triggers = set()

        for item in self.config:
            event_trigger = EventTrigger(self.machine, item, self.config[item])
            self.event_triggers.add(event_trigger)


class EventTrigger(object):

    def __init__(self, machine, name, config):
        self.log = logging.getLogger('EventTrigger.' + name)
        self.machine = machine
        self.name = name
        self.config = config
        self.enabled = False
        self.num_hits = 0
        self.ignore_hits = False

        self.delay = DelayManager()

        # todo settle time

        if 'trigger_events' not in self.config:
            return  # Not much point to continue here
        else:
            self.config['trigger_events'] = self.machine.string_to_list(
                self.config['trigger_events'])

        if 'event_when_hit' not in self.config:
            self.config['event_when_hit'] = 'eventtrigger_' + self.name + '_hit'

        if 'hits_to_complete' not in self.config:
            self.config['hits_to_complete'] = 1

        if 'multiple_hit_window' not in self.config:
            self.config['multiple_hit_window'] = None
        else:
            self.config['multiple_hit_window'] = Timing.string_to_ms(
                self.config['multiple_hit_window'])

        if 'enable_events' not in self.config:
            self.config['enable_events'] = None
        else:
            self.config['enable_events'] = self.machine.string_to_list(
                self.config['enable_events'])

        if 'disable_events' not in self.config:
            self.config['disable_events'] = None
        else:
            self.config['disable_events'] = self.machine.string_to_list(
                self.config['disable_events'])

        if 'reset_events' not in self.config:
            self.config['reset_events'] = None
        else:
            self.config['reset_events'] = self.machine.string_to_list(
                self.config['reset_events'])

        if 'event_when_complete' not in self.config:
            self.config['event_when_complete'] = (
                'eventtrigger_' + self.name + '_complete')

        if 'settle_time' not in self.config:
            self.config['settle_time'] = None
        else:
            self.config['settle_time'] = Timing.string_to_ms(
                self.config['settle_time'])

        # register for events

        for event in self.config['enable_events']:
            self.machine.events.add_handler(event, self.enable)
        for event in self.config['disable_events']:
            self.machine.events.add_handler(event, self.disable)
        for event in self.config['reset_events']:
            self.machine.events.add_handler(event, self.reset)

    def enable(self, **kwargs):
        """Enables this trigger. Automatically called when one of the
        'enable_event's is posted. Can also manually be called.
        """
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        for event in self.config['trigger_events']:
            self.machine.events.add_handler(event, self.hit)

        self.enabled = True

    def disable(self, **kwargs):
        """Enables this trigger. Automatically called when one of the
        'disable_event's is posted. Can also manually be called.
        """
        self.machine.events.remove_handler(self.hit)

        self.enabled = False

    def reset(self, **kwargs):
        """Resets the hit progress towards completion"""
        self.num_hits = 0

    def hit(self, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the 'trigger_events's is posted. Can also manually be
        called.
        """
        if not self.ignore_hits:
            self.num_hits += 1

            if self.num_hits >= self.config['hits_to_complete']:
                self.complete()

            if self.config['event_when_hit']:
                self.machine.events.post(self.config['event_when_hit'],
                                         hits=self.num_hits)

            if self.config['multiple_hit_window']:
                self.ignore_hits = True
                self.delay('ignore_hits_within_window',
                           self.config['multiple_hit_window'],
                           self.stop_ignoring_hits)

    def stop_ignoring_hits(self):
        """Causes the EventTrigger to stop ignoring subsequent hits that occur
        within the 'multiple_hit_window'. Automatically called when the window
        time expires. Can safely be manually called.
        """
        self.ignore_hits = False

    def complete(self):
        if self.config['event_when_complete']:
            self.machine.events.post(self.config['event_when_complete'],
                                     hits=self.num_hits)
        self.reset()





