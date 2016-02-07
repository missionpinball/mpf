""" MPF plugin for a score controller which handles all scoring and bonus
tracking.
"""

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
        self.mode_configs[mode] = config
        self.mode_scores[mode] = dict()
        self.mode_configs = OrderedDict(sorted(iter(self.mode_configs.items()),
                                               key=lambda x: x[0].priority,
                                               reverse=True))
        for event in list(config.keys()):
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

        for entry_mode, settings in self.mode_configs.items():
            if event_name in settings:
                for var_name, value in settings[event_name].items():

                    if (type(value) is int and
                            entry_mode == mode and
                            var_name not in blocked_variables):
                        self.add(value, var_name, mode)

                    elif type(value) is str:
                        value, block = value.split('|')
                        if (entry_mode == mode and
                                    var_name not in blocked_variables):
                            self.add(value, var_name, mode)
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
