""" MPF plugin for a score controller which handles all scoring and bonus
tracking."""
# scoring.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import OrderedDict

class ScoreController(object):

    def __init__(self, machine):
        """Base class for the score controller which is responsible for
        tracking scoring events (or any events configured to score) and adding
        them to the current player's score.)

        TODO: There's a lot to do here, including bonus scoring & multipliers.

        """
        self.machine = machine
        self.log = logging.getLogger("Score")
        self.log.debug("Loading the Score Controller")

        self.machine.mode_controller.register_start_method(self.mode_start,
                                                           'scoring')
        self.mode_configs = OrderedDict()
        self.mode_scores = dict()

    def mode_start(self, config, mode, priority, **kwargs):
        # config is localized

        self.mode_configs[mode] = config
        self.mode_scores[mode] = dict()
        self.mode_configs = OrderedDict(sorted(self.mode_configs.iteritems(),
                                               key=lambda x: x[0].priority,
                                               reverse=True))
        for event in config.keys():
            mode.add_mode_event_handler(event, self._score_event_callback,
                                        priority, event_name=event)

        return self.mode_stop, mode

    def mode_stop(self, mode, **kwargs):
        try:
            del self.mode_configs[mode]
        except KeyError:
            pass

        try:
            del self.mode_scores[mode]
        except KeyError:
            pass

    def _score_event_callback(self, event_name, mode, **kwargs):
        if not (self.machine.game.player and self.machine.game.balls_in_play):
            return

        blocked_variables = set()

        for entry_mode, settings in self.mode_configs.iteritems():

            if event_name in settings:
                for var_name, value in settings[event_name].iteritems():

                    if (type(value) is int and
                            entry_mode == mode and
                            var_name not in blocked_variables):
                        self.add(value, var_name, mode)
                        break
                    elif type(value) is str:
                        value, block = value.split('|')

                        if entry_mode == mode and value not in blocked_variables:
                            self.add(value, var_name, mode)
                            break

                        if block.lower() == 'block':
                            blocked_variables.add(var_name)

    def add(self, value, var_name='score', mode=None):
        if not value:
            return

        value = int(value)
        prev_value = value
        self.machine.game.player[var_name] += value

        if mode:
            self.mode_scores[mode][var_name] = (
                self.mode_scores[mode].get(var_name, 0) + value)
            self.machine.events.post('_'.join(('mode', mode.name, var_name,
                                               'score')), value=value,
                                     prev_value=prev_value,
                                     change=value-prev_value)


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
