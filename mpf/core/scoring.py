"""MPF device for a score controller which handles all scoring and bonus tracking."""
import logging
from collections import OrderedDict, namedtuple

from mpf.core.machine import MachineController
from mpf.core.mode import Mode

ScoreEntry = namedtuple("ScoreEntry", ["var", "value", "block"])


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
        self.mode_scores = {}
        self.score_events = {}

    @classmethod
    def _validate_entry(cls, entry, mode):
        entries = []
        for var, value in entry.items():
            if isinstance(value, int):
                entries.append(ScoreEntry(var, value, False))
            elif isinstance(value, str):
                try:
                    value, block = value.split('|')
                    if block != "block":
                        raise AssertionError("Invalid action in scoring entry: {} in mode {}".format(
                            entry, mode.name))
                    entries.append(ScoreEntry(var, int(value), True))
                except ValueError:
                    raise AssertionError("Invalid scoring entry: {} in mode {}".format(
                        entry, mode.name))
        return entries

    def mode_start(self, config: dict, mode: Mode, priority: int, **kwargs):
        """Called when mode is started.

        Args:
            config: Config dict inside mode.
            mode: Mode which was started.
            priority: Priority of mode.
        """
        del kwargs
        self.mode_configs[mode] = {}
        self.mode_scores[mode] = dict()
        self.mode_configs = OrderedDict(sorted(iter(self.mode_configs.items()),
                                               key=lambda x: x[0].priority,
                                               reverse=True))

        for event in config:
            self.mode_configs[mode][event] = self._validate_entry(config[event], mode)

            if event not in self.score_events:
                self.score_events[event] = self.machine.events.add_handler(
                    event, self._score_event_callback, priority, event_name=event)

        return self.mode_stop, mode

    def mode_stop(self, mode, **kwargs):
        """Called when mode is stopped.

        Args:
            mode: Mode which was stopped.
        """
        del kwargs
        try:
            # we could unregister the event handlers here if this causes any problems
            del self.mode_configs[mode]
        except KeyError:
            pass

        try:
            del self.mode_scores[mode]
        except KeyError:
            pass

    def _score_event_callback(self, event_name, **kwargs):
        del kwargs
        if not (self.machine.game.player and self.machine.game.balls_in_play):
            return

        blocked_variables = set()

        for entry_mode, settings in self.mode_configs.items():
            if event_name in settings:
                for score_entry in settings[event_name]:
                    if score_entry.var in blocked_variables:
                        continue

                    if score_entry.block:
                        blocked_variables.add(score_entry.var)
                    self.add(score_entry.value, score_entry.var, entry_mode)

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
