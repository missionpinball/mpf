"""Scoring Config Player."""
from collections import namedtuple
from typing import Dict, List, Any

from mpf.core.config_player import ConfigPlayer
from mpf.core.machine import MachineController

VarBlock = namedtuple("VarBlock", ["priority", "context"])


class ScorePlayer(ConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'scoring'
    show_section = 'score'

    def __init__(self, machine: MachineController) -> None:
        """Initialise score player."""
        super().__init__(machine)
        self.blocks = {}    # type: Dict[str, List[VarBlock]]

    @staticmethod
    def is_entry_valid_outside_mode(settings: dict) -> bool:
        """Return true if this entry may run without a game and player."""
        del settings
        return False

    def play(self, settings: dict, context: str, calling_context: str,
             priority: int = 0, **kwargs) -> None:
        """Score variable."""
        for var, s in settings.items():
            if var == "block":
                raise AssertionError('Do not use "block" as variable name in score_player.')

            if s['condition'] and not s['condition'].evaluate(kwargs):
                continue

            block_item = var + ":" + calling_context
            if self._is_blocked(block_item, context, priority):
                continue
            if s['block']:
                if block_item not in self.blocks:
                    self.blocks[block_item] = []
                if VarBlock(priority, context) not in self.blocks[block_item]:
                    self.blocks[block_item].append(VarBlock(priority, context))

            self._score(var, s, kwargs)

    def _is_blocked(self, block_item: str, context: str,
                    priority: int) -> bool:
        if block_item not in self.blocks or not self.blocks[block_item]:
            return False
        priority_sorted = sorted(self.blocks[block_item], reverse=True)
        first_element = priority_sorted[0]
        return first_element.priority > priority and first_element.context != context

    def _score(self, var: str, entry: dict,
               placeholder_parameters: dict) -> None:
        if entry['string']:
            self.machine.game.player[var] = entry['string']
            return

        # evaluate placeholder
        if entry['float']:
            value = entry['float'].evaluate(placeholder_parameters)
        else:
            value = entry['score'].evaluate(placeholder_parameters)

        if entry['action'] == "add":
            if entry['player']:
                # specific player
                self.machine.game.player_list[entry['player'] - 1][var] += value
            else:
                # default to current player
                self.machine.game.player[var] += value
        elif entry['action'] == "set":
            if entry['player']:
                # specific player
                self.machine.game.player_list[entry['player'] - 1][var] = value
            else:
                # default to current player
                self.machine.game.player[var] = value
        elif entry['action'] == "add_machine":
            old_value = self.machine.get_machine_var(var)
            if old_value is None:
                old_value = 0
            self.machine.set_machine_var(var, old_value + value)
        elif entry['action'] == "set_machine":
            self.machine.set_machine_var(var, value)
        else:
            raise AssertionError("Invalid value: {}".format(entry))

    def clear_context(self, context: str) -> None:
        """Clear context."""
        for var in self.blocks:
            for entry, s in enumerate(self.blocks[var]):
                if s.context == context:
                    del self.blocks[var][entry]

    def validate_config_entry(self, settings: dict, name: str) -> dict:
        """Validate one entry of this player."""
        config = {}
        if not isinstance(settings, dict):
            raise AssertionError("Settings of score_player {} should "
                                 "be a dict. But are: {}".format(name, settings))
        for var, s in settings.items():
            var_dict = self.machine.placeholder_manager.parse_conditional_template(var)
            score_dict = self._parse_config(s, name)
            score_dict["condition"] = var_dict["condition"]
            config[var_dict["name"]] = score_dict
        return config

    def get_express_config(self, value: Any) -> dict:
        """Parse express config."""
        if not isinstance(value, str):
            block = False
        else:
            try:
                value, block_str = value.split('|')
            except ValueError:
                block = False
            else:
                if block_str != "block":
                    raise AssertionError(
                        "Invalid action in scoring entry: {}".format(value))
                block = True

        return {"score": value, "block": block}

    def get_list_config(self, value: Any):
        """Parse list."""
        raise AssertionError("Score player does not support lists.")
