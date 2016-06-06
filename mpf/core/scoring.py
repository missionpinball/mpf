"""MPF device for a score controller which handles all scoring and bonus tracking."""

import logging
from collections import OrderedDict

from mpf.core.machine import MachineController
from mpf.core.mode import Mode


class ScoreController(object):

    """Base class for the score controller.

    It is responsible for tracking scoring events (or any events configured to score) and adding
    them to the current player's score.
    """

    def __init__(self, machine: MachineController):
        """Initialise Score Controller."""
        self.machine = machine
        self.log = logging.getLogger("Score")
        self.log.debug("Loading the Score Controller")

        self.machine.mode_controller.register_start_method(self.mode_start,
                                                           'scoring')
        self.mode_configs = OrderedDict()
        self.mode_scores = dict()

    @classmethod
    def _validate_entry(cls, entry, mode):
        for value in entry.values():
            if isinstance(value, int):
                continue
            elif isinstance(value, str):
                try:
                    value, block = value.split('|')
                    int(value)
                    if block != "block":
                        raise AssertionError("Invalid action in scoring entry: {} in mode {}".format(
                            entry, mode.name))
                except ValueError:
                    raise AssertionError("Invalid scoring entry: {} in mode {}".format(
                        entry, mode.name))

    def mode_start(self, config: dict, mode: Mode, priority: int, **kwargs):
        """Called when mode is started.

        Args:
            config: Config dict inside mode.
            mode: Mode which was started.
            priority: Priority of mode.
        """
        del kwargs
        self.mode_configs[mode] = config
        self.mode_scores[mode] = dict()
        self.mode_configs = OrderedDict(sorted(iter(self.mode_configs.items()),
                                               key=lambda x: x[0].priority,
                                               reverse=True))

        for event in list(config.keys()):
            self._validate_entry(config[event], mode)

            mode.add_mode_event_handler(event, self._score_event_callback,
                                        priority, event_name=event)

        return self.mode_stop, mode

    def mode_stop(self, mode, **kwargs):
        """Called when mode is stopped.

        Args:
            mode: Mode which was stopped.
        """
        del kwargs
        try:
            del self.mode_configs[mode]
        except KeyError:
            pass

        try:
            del self.mode_scores[mode]
        except KeyError:
            pass

    def _score_event_callback(self, event_name, mode, **kwargs):
        del kwargs
        if not (self.machine.game.player and self.machine.game.balls_in_play):
            return

        blocked_variables = set()

        for entry_mode, settings in self.mode_configs.items():
            if event_name in settings:
                for var_name, value in settings[event_name].items():

                    if (isinstance(value, int) and
                            entry_mode == mode and
                            var_name not in blocked_variables):
                        self.add(value, var_name, mode)

                    elif isinstance(value, str):
                        value, block = value.split('|')
                        if entry_mode == mode and var_name not in blocked_variables:
                            self.add(value, var_name, mode)
                        if block.lower() == 'block':
                            blocked_variables.add(var_name)

    def add(self, value: int, var_name: str='score', mode: Mode=None):
        """Add score to current player.

        Args:
            value: The score to add.
            var_name: Player variable to use for the score.
            mode: Mode in which this was scored. Used track mode scores and post events.
        """
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
                                     change=value - prev_value)
            '''event: mode_(mode_name)_(var_name)_score

            desc: A scoring event was just processed to add (or remove) value
            from a player variable. (Remember that scoring events can affect
            the value of *any* player variable, not just the *score* player
            variable.

            For example, if a scoring event in the "base" mode added to the
            player variable called *ramps*, the event posted would be
            *mode_base_ramps_score*.

            args:
            value: The new value of the player variable.
            prev_value: The previous value of this player variable before the
                new *value* was added.
            change: The numeric value of the change. (*value* minus
                *prev_value*).
            '''
