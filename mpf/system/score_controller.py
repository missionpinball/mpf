""" Base class for the score controller which handles all scoring and bonus
tracking."""
# score_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework
import logging


class ScoreController(object):

    def __init__(self, machine):
        """Base class for the score controller which is responsible for
        tracking scoring events (or any events configured to score) and adding
        them to the current player's score.)

        TODO: There's a lot to do here, including bonus scoring & multipliers.

        """
        self.machine = machine
        self.log = logging.getLogger("Score")
        self.log.debug("Loading the ScoreController")
        self.score_events = {}

        if 'Scoring' in self.machine.config:
            self.log.debug("Configuring the Score Controller")
            for score_event in self.machine.config['Scoring']:

                # figure out the event name
                if score_event.startswith('_'):
                    event_name = score_event[1:]
                else:
                    event_name = "shot_" + score_event

                # figure out the points
                points = self.machine.config['Scoring'][score_event]['Score']

                self.register_score_event(event_name, points)
        else:
            self.log.debug("No shot configuration found. Skipping...")

    def register_score_event(self, event_name, points):
        """Used to register a score event which adds to a player's score when
        a certain event is posted.

        Paramters
        ---------

        event_name : str
            The name of the event that should cause a score change to take
            place.

        points : int
            The number of points that should be added or subtracted to the
            current player's score when this event is posted.

        """
        self.log.debug("Registering score event '%s' with: %s", event_name,
                       points)
        self.score_events[event_name] = int(points)

        self.machine.events.add_handler(event_name, self._score_event_callback,
                                        1, scoring_event=event_name)

    def add(self, points):
        """Adds to the current player's score.

        Use this method instead of changing the value of the player attribute
        directly because this method will post the scoring events that other
        modules use for effects and stuff.

        Parameters
        ----------

        points : int
            The number of points to add to the current player's score. Note
            this value can also be negative to subtract points from their
            score.

        """

        self.machine.game.player.vars['score'] += int(points)
        self.log.debug("Current player's score: %s",
                       self.machine.game.player.vars['score'])
        self.machine.events.post('score_change', change=points,
                                 score=self.machine.game.player.vars['score'])

    def _score_event_callback(self, scoring_event):
        # Processes the scoring events
        if self.machine.game and self.machine.game.player:
            self.log.debug("Score Event '%s', Increasing score by %s",
                           scoring_event, self.score_events[scoring_event])
            self.add(self.score_events[scoring_event])

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
