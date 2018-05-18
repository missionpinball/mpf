"""Block Event Config Player."""
from mpf.core.config_player import ConfigPlayer


class BlockEventPlayer(ConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'blocking'

    __slots__ = []

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Block event."""
        min_priority = kwargs.get("_min_priority", {"all": 0})

        for facility, min_priority_facility in settings.items():
            if min_priority_facility is True:
                min_priority_facility = priority
            elif min_priority_facility > priority:
                raise AssertionError("Cannot block above own priority. {} {}".format(facility, min_priority_facility))
            if facility not in min_priority or min_priority[facility] < min_priority_facility:
                min_priority[facility] = min_priority_facility

        return {"_min_priority": min_priority}

    def validate_config_entry(self, settings: dict, name: str) -> dict:
        """Validate one entry of this player."""
        return settings

    def get_express_config(self, value):
        """Parse short config."""
        raise AssertionError()
