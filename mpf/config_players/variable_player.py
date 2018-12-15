"""Variable Config Player (used for scoring and more)."""
import re
from collections import namedtuple
from typing import Dict, List, Any

from mpf.core.config_player import ConfigPlayer
from mpf.core.machine import MachineController

VarBlock = namedtuple("VarBlock", ["priority", "context"])


class VariablePlayer(ConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'variable_player'
    show_section = 'variables'

    __slots__ = ["blocks"]

    def __init__(self, machine: MachineController) -> None:
        """Initialise variable player."""
        super().__init__(machine)
        self.blocks = {}    # type: Dict[str, List[VarBlock]]

    @staticmethod
    def is_entry_valid_outside_mode(settings: dict) -> bool:
        """Return true if this entry may run without a game and player."""
        for event, setting in settings.items():
            del event
            if setting['action'] not in ("set_machine", "add_machine"):
                return False

        # true if only set_machine or add_machine are used
        return True

    def play(self, settings: dict, context: str, calling_context: str,
             priority: int = 0, **kwargs) -> None:
        """Variable name."""
        for var, s in settings.items():
            if var == "block":
                self.raise_config_error('Do not use "block" as variable name in variable_player.', 1, context=context)

            if s['action'] in ("add", "add_machine") and s['string']:
                self.raise_config_error('Cannot add two strings. Use action set or set_machine.', 3, context=context)

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

            self._set_variable(var, s, kwargs, context)

    def _is_blocked(self, block_item: str, context: str,
                    priority: int) -> bool:
        if block_item not in self.blocks or not self.blocks[block_item]:
            return False
        priority_sorted = sorted(self.blocks[block_item], reverse=True)
        first_element = priority_sorted[0]
        return first_element.priority > priority and first_element.context != context

    def _set_variable(self, var: str, entry: dict, placeholder_parameters: dict, context) -> None:
        # evaluate placeholder
        if entry['float']:
            value = entry['float'].evaluate(placeholder_parameters)
        elif entry['int']:
            value = entry['int'].evaluate(placeholder_parameters)
        elif entry['string']:
            value = entry['string']
        else:
            value = None    # prevent type confusion
            self.raise_config_error("You need to either set float, int or string", 2, context=context)

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
            self.raise_config_error("Invalid value: {}".format(entry), 8, context=context)

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
            self.raise_config_error("Settings of variable_player should "
                                    "be a dict. But are: {}".format(settings), 5, context=name)
        for var, s in settings.items():
            var_dict = self.machine.placeholder_manager.parse_conditional_template(var)
            value_dict = self._parse_config(s, name)
            value_dict["condition"] = var_dict["condition"]
            config[var_dict["name"]] = value_dict
            if not bool(re.match('^[0-9a-zA-Z_-]+$', var_dict["name"])):
                self.raise_config_error("Variable may only contain letters, numbers, dashes and underscores. "
                                        "Name: {}".format(var_dict["name"]), 4, context=name)
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
                    self.raise_config_error("Invalid action in variable_player entry: {}".format(value), 6)
                block = True

        return {"int": value, "block": block}

    def get_list_config(self, value: Any):
        """Parse list."""
        self.raise_config_error("Variable player does not support lists.", 7)
