"""Base class for flat config players."""
import abc

from mpf.core.config_player import ConfigPlayer


class FlatConfigPlayer(ConfigPlayer, metaclass=abc.ABCMeta):

    """Flat show players."""

    __slots__ = []

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = self._parse_config(settings, name)
        return config

    def get_full_config(self, value):
        """Return full config."""
        for element in value:
            value[element] = super().get_full_config(value[element])
        return value

    @abc.abstractmethod
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Directly play player."""
        # **kwargs since this is an event callback
        raise NotImplementedError

    @abc.abstractmethod
    def get_express_config(self, value):
        """Parse short config version.

        Implements "express" settings for this config_player which is what
        happens when a config is passed as a string instead of a full config
        dict. (This is detected automatically and this method is only called
        when the config is not a dict.)

        For example, the led_player uses the express config to parse a string
        like 'ff0000-f.5s' and translate it into:

        color: 220000
        fade: 500

        Since every config_player is different, this method raises a
        NotImplementedError and most be configured in the child class.

        Args:
            value: The single line string value from a config file.

        Returns:
            A dictionary (which will then be passed through the config
            validator)

        """
        raise NotImplementedError(self.config_file_section)
