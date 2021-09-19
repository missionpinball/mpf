"""Score Queue player for SS style scoring."""
from typing import List, Any

from mpf.core.config_player import ConfigPlayer


class ScoreQueuePlayer(ConfigPlayer):

    """SS style scoring based on config."""

    config_file_section = 'score_queue_player'
    show_section = 'score_queues'

    __slots__ = []  # type: List[str]

    @staticmethod
    def is_entry_valid_outside_mode(settings) -> bool:
        """Score queue is only valid in game."""
        del settings
        return False

    def play(self, settings: dict, context: str, calling_context: str,
             priority: int = 0, **kwargs) -> None:
        """Variable name."""
        for var, s in settings.items():
            if s['condition'] and not s['condition'].evaluate(kwargs):
                continue
            self.machine.score_queues[var].score(s['int'].evaluate(kwargs))

    def validate_config_entry(self, settings: dict, name: str) -> dict:
        """Validate one entry of this player."""
        config = {}
        if not isinstance(settings, dict):
            self.raise_config_error("Settings of score_queue_player should "
                                    "be a dict. But are: {}".format(settings), 5, context=name)
        for var, s in settings.items():
            var_conditional_event = self._parse_and_validate_conditional(var, name)
            value_dict = self._parse_config(s, name)
            value_dict["condition"] = var_conditional_event.condition
            config[var_conditional_event.name] = value_dict
        return config

    def get_express_config(self, value: Any) -> dict:
        """Parse express config."""
        return {"int": value}
