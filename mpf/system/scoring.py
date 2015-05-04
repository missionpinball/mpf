""" MPF plugin for a score controller which handles all scoring and bonus
tracking."""
# score_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import uuid


class ScoreController(object):

    def __init__(self, machine):
        """Base class for the score controller which is responsible for
        tracking scoring events (or any events configured to score) and adding
        them to the current player's score.)

        TODO: There's a lot to do here, including bonus scoring & multipliers.

        """
        self.machine = machine
        self.machine.score = self
        self.log = logging.getLogger("Score")
        self.log.debug("Loading the Score Controller")
        self.score_events = dict()

        if 'scoring' in self.machine.config:
            self.process_config(self.machine.config['scoring'])

        # Tell the mode controller that it should look for scoring items in
        # modes.
        self.machine.modes.register_start_method(self.process_config, 'scoring')

    def process_config(self, config, mode=None, priority=0):
        # config is Scoring subsection of config dict

        self.log.debug("Processing Scoring configuration. Base Priority: %s",
                       priority)

        key_list = list()

        for score_event in config:

            if 'score' in config[score_event] and config[score_event]['score']:
                points = config[score_event]['score']

            if 'block' in config[score_event] and config[score_event]['block']:
                block = True
            else:
                block = False

            key_list.append(self.register_score_event(score_event, points,
                                                      priority, block))

        return self.unload_score_events, key_list

    def unload_score_events(self, key_list):
        """Unloads and removes several score events at once.

        Args:
            key_list: A list of keys of the score events you want to remove.
        """
        self.log.debug("Unloading scoring events")
        for key in key_list:
            self.unregister_score_event(key)

    def register_score_event(self, event_name, points, priority=0, block=False):
        """Used to register a score event which adds to a player's score when
        a certain event is posted.

        Args:
            event_name : The string name of the event that should cause a score
                change to take place.
            points : The integer number of points that should be added or
                subtracted to the current player's score when this event is
                posted.
            priority: Integer priority which is used in conjunction with block.
            block: Boolean which specifies whether this event should block lower
                priority events. If True, lower priority events will not score
                as long as this event is registered. If False then lower
                priority events will score as normal.

        Returns: A "key" which can be used to later unregister this event via
            the 'unregister_score_event' method.
        """
        self.log.debug("Registering score event '%s' with: %s", event_name,
                       points)

        if event_name not in self.score_events:
            self.score_events[event_name] = list()

        score_entry_dict = dict()
        score_entry_dict['points'] = int(points)
        score_entry_dict['priority'] = priority
        score_entry_dict['score_entry_key'] = uuid.uuid4()

        if block:
            score_entry_dict['block'] = priority
        else:
            score_entry_dict['block'] = None

        score_entry_dict['event_key'] = self.machine.events.add_handler(
            event=event_name,
            handler=self._score_event_callback,
            score_priority=priority,
            score_event=event_name,
            score_entry_key=score_entry_dict['score_entry_key'],
            block=block)

        self.score_events[event_name].append(score_entry_dict)

        # Sort the list so the highest priority entries are first
        self.score_events[event_name] = (
            sorted(self.score_events[event_name],
                   key=lambda k: k['priority'],
                   reverse=True))

        return score_entry_dict['score_entry_key']

    def unregister_score_event(self, score_entry_key):
        """Removes a score event.

        Args:
            score_entry_key: The key of the score event to remove. This is the
                key that's returned by the 'register_score_event()' method.
        """

        event_key = None

        for event, score_entry_list in self.score_events.iteritems():

            for score_entry_dict in score_entry_list:
                if score_entry_dict['score_entry_key'] == score_entry_key:
                    event_key = score_entry_dict['event_key']
                    self.log.debug("Removing score event '%s' for '%s' points",
                                   event, score_entry_dict['points'])
                    self.score_events[event].remove(score_entry_dict)
                    break
            else:
                continue
            break

        if not self.score_events[event]:
            del self.score_events[event]

        if event_key:
            self.machine.events.remove_handler_by_key(event_key)

    def add(self, points, force=False):
        """Adds to the current player's score.

        Use this method instead of changing the value of the player attribute
        directly because this method will post the scoring events that other
        modules use for effects and stuff.

        Args:
            points : Integer of points to add to the current player's score.
                Note this value can also be negative to subtract points from
                their score.
        """

        # Only process scores if there's at least one ball in play
        if not self.machine.game or not self.machine.game.num_balls_in_play:
            if not force:
                return

        self.machine.game.player.score += int(points)

    def _score_event_callback(self, score_event, score_entry_key,
                              score_priority, block, **kwargs):
        # Processes the scoring events

        # todo
        # look at the event that came in and get its priority
        # see if there are any other registered handlers at a higher
        # priority with block enabled
        # if so, do nothing. If not, do the score

        if self.machine.game and self.machine.game.num_balls_in_play:

            # try because it's possible this score entry was removed between
            # the time the event was posted and it was processed
            #try:

            # Loop through all the score events for this event
            for score_event_dict in self.score_events[score_event]:
                # If it finds one with 'block', and the priority of the
                # block is higher than the current priority, don't process
                if (score_event_dict['block'] and
                        score_event_dict['priority'] >
                        score_priority):
                    return

                if score_event_dict['score_entry_key'] == score_entry_key:

                    self.log.debug("Score Event increasing score by %s",
                                   score_event_dict['points'])
                    self.add(score_event_dict['points'])
            #except:
            #    pass

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
