"""Error in MPF or MPF-MC."""
from mpf._version import log_url


class BaseError(AssertionError):

    """Error in a config file found."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, message, error_no, logger_name, context=None, url_name=None):
        """Initialise exception."""
        self._logger_name = logger_name
        self._error_no = error_no
        self._context = context
        self._message = message
        if url_name:
            self._url_name = url_name
        else:
            self._url_name = logger_name
        super().__init__(message)

    def get_error_no(self):
        """Return error no."""
        return self._error_no

    def get_context(self):
        """Return error no."""
        return self._context

    def get_logger_name(self):
        """Return error no."""
        return self._logger_name

    def get_short_name(self):
        """Return short name."""
        raise NotImplementedError

    def get_long_name(self):
        """Return long name."""
        raise NotImplementedError

    def extend(self, message):
        """Chain a new message onto an existing error, keeping the original error's logger, context, and error_no."""
        self._message = "{} >> {}".format(message, self._message)
        super().__init__(self._message)

    def __str__(self):
        """Return nice string."""
        error_slug = "{}-{}-{}".format(self.get_short_name(), self._url_name.replace(" ", "_"), self._error_no)
        error_url = log_url.format(error_slug)
        if self._context:
            return "{} in {}: {} Context: {} Error Code: {} ({})".format(
                self.get_long_name(), self._logger_name, super().__str__(), self._context, error_slug, error_url)

        return "{} in {}: {} Error Code: {} ({})".format(
            self.get_long_name(), self._logger_name, super().__str__(), error_slug, error_url)
