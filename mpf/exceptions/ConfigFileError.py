"""Config file error in a MPF config file."""


class ConfigFileError(AssertionError):

    """Error in a config file found."""

    def __init__(self, message, error_no, logger_name):
        """Initialise exception."""
        self._logger_name = logger_name
        self._error_no = error_no
        super().__init__(message)

    def __str__(self):
        """Return nice string."""
        return "Config File Error in {}: {} Error Code: CFE-{}-{}".format(
            self._logger_name, super().__str__(), self._logger_name, self._error_no)
