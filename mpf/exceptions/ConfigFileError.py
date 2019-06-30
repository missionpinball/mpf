"""Config file error in a MPF config file."""
from mpf._version import log_url


class ConfigFileError(AssertionError):

    """Error in a config file found."""

    def __init__(self, message, error_no, logger_name, context=None):
        """Initialise exception."""
        self._logger_name = logger_name
        self._error_no = error_no
        self._context = context
        super().__init__(message)

    def __str__(self):
        """Return nice string."""
        error_slug = "CFE-{}-{}".format(self._logger_name, self._error_no)
        error_url = log_url.format(error_slug)
        if self._context:
            return "Config File Error in {}: {} Context: {} Error Code: {} ({})".format(
                self._logger_name, super().__str__(), self._context, error_slug, error_url)
        else:
            return "Config File Error in {}: {} Error Code: {} ({})".format(
                self._logger_name, super().__str__(), error_slug, error_url)
