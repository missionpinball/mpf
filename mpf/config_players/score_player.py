"""Scoring Config Player."""
from mpf.core.config_player import ConfigPlayer


class ScorePlayer(ConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'scoring'
    show_section = 'score'
    device_collection = None

    def __init__(self, machine):
        """Initialise score player."""
        super().__init__(machine)
        self.blocks = {}

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Score variable."""
        for var, s in settings.items():
            if self._is_blocked(var, context, calling_context):
                continue
            if s['block']:
                if var not in self.blocks:
                    self.blocks[var] = []
                if (priority, context, calling_context) not in self.blocks[var]:
                    self.blocks[var].append((priority, context, calling_context))

            self._score(var, s)

    def _is_blocked(self, var, context, calling_context):
        if var not in self.blocks or not self.blocks[var]:
            return False
        priority_sorted = sorted(self.blocks[var], reverse=True)
        return priority_sorted[0][1] != context + "_" + calling_context

    def _score(self, var, entry):
        if entry['string']:
            self.machine.game.player[var] = entry['string']
        elif entry['action'] == "add":
            self.machine.game.player[var] += entry['score'].evaluate([])
        elif entry['action'] == "set":
            self.machine.game.player[var] = entry['score'].evaluate([])
        else:
            raise AssertionError("Invalid value: {}".format(entry))

    def clear_context(self, context):
        """Clear context."""
        for var in self.blocks:
            for entry, s in enumerate(self.blocks[var]):
                if s[1] == context:
                    del self.blocks[var][entry]

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = {}
        for var, s in settings.items():
            config[var] = self._parse_config(s, name)
        return config

    def get_express_config(self, value):
        """Parse express config."""
        if isinstance(value, int):
            block = False
        else:
            try:
                value, block = value.split('|')
            except ValueError:
                block = False
            else:
                if block != "block":
                    raise AssertionError("Invalid action in scoring entry: {}".format(value))
                block = True

        return {"score": value, "block": block}

    def get_list_config(self, value):
        """Parse list."""
        raise AssertionError("Score player does not support lists.")


player_cls = ScorePlayer
