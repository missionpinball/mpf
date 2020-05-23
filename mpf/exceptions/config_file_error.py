"""Config file error in a MPF config file."""
from mpf.exceptions.base_error import BaseError


class ConfigFileError(BaseError):

    """Error in a config file found."""

    def get_short_name(self):
        """Return short name."""
        return "CFE"

    def get_long_name(self):
        """Return long name."""
        return "Config File Error"
