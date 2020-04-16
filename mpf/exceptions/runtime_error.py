"""Runtime error in MPF or MPF-MC."""
from mpf.exceptions.base_error import BaseError


class MpfRuntimeError(BaseError):

    """Runtime error."""

    def get_short_name(self):
        """Return short name."""
        return "RE"

    def get_long_name(self):
        """Return long name."""
        return "Runtime Error"
