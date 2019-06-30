"""Contains the LogMixin class."""
import logging

from mpf.exceptions.ConfigFileError import ConfigFileError
from mpf._version import log_url

MYPY = False
if MYPY:   # pragma: no cover
    from logging import Logger


class LogMixin:

    """Mixin class to add smart logging functionality to modules."""

    unit_test = False

    __slots__ = ["log", "_info_to_console", "_debug_to_console", "_info_to_file", "_debug_to_file"]

    def __init__(self) -> None:
        """Initialise Log Mixin."""
        self.log = None     # type: Logger
        self._info_to_console = False
        self._debug_to_console = False
        self._info_to_file = False
        self._debug_to_file = False

        logging.addLevelName(21, "INFO")
        logging.addLevelName(11, "DEBUG")
        logging.addLevelName(22, "INFO")
        logging.addLevelName(12, "DEBUG")

    @property
    def _info(self):
        return self._info_to_console or self._info_to_file

    @property
    def _debug(self):
        return self._debug_to_console or self._debug_to_file

    def configure_logging(self, logger: str, console_level: str = 'basic',
                          file_level: str = 'basic'):
        """Configure logging.

        Args:
            logger: The string name of the logger to use.
            console_level: The level of logging for the console. Valid options
                are "none", "basic", or "full".
            file_level: The level of logging for the console. Valid options
                are "none", "basic", or "full".
        """
        self.log = logging.getLogger(logger)
        if hasattr(self, "machine") and self.machine and self.machine.options['production']:
            return

        try:
            if console_level.lower() == 'basic':
                self._info_to_console = True
            elif console_level.lower() == 'full':
                self._debug_to_console = True
        except AttributeError:
            pass

        try:
            if file_level.lower() == 'basic':
                self._info_to_file = True
            elif file_level.lower() == 'full':
                self._debug_to_file = True
        except AttributeError:
            pass

        # in unit tests always log info. debug will depend on the actual settings.
        if self.unit_test:
            self._info_to_console = True

    def debug_log(self, msg: str, *args, context=None, error_no=None, **kwargs) -> None:
        """Log a message at the debug level.

        Note that whether this message shows up in the console or log file is
        controlled by the settings used with configure_logging().
        """
        if not hasattr(self, 'log'):
            self._logging_not_configured()

        if self._debug_to_console:
            level = 12
        elif self._debug_to_file:
            level = 11
        else:
            return

        if not self.log.isEnabledFor(level):
            return

        self.log.log(level, self.format_log_line(msg, context, error_no), *args, **kwargs)

    def info_log(self, msg: str, *args, context=None, error_no=None, **kwargs) -> None:
        """Log a message at the info level.

        Whether this message shows up in the console or log file is controlled
        by the settings used with configure_logging().
        """
        if not self.log:
            self._logging_not_configured()

        if self._info_to_console or self._debug_to_console:
            level = 22
        elif self._info_to_file or self._debug_to_file:
            level = 21
        else:
            return

        if not self.log.isEnabledFor(level):
            return

        self.log.log(level, self.format_log_line(msg, context, error_no), *args, **kwargs)

    def warning_log(self, msg: str, *args, context=None, error_no=None, **kwargs) -> None:
        """Log a message at the warning level.

        These messages will always be shown in the console and the log file.
        """
        if not self.log:
            self._logging_not_configured()

        if not self.log.isEnabledFor(30):
            return

        self.log.log(30, self.format_log_line(msg, context, error_no), *args, **kwargs)

    def error_log(self, msg: str, *args, context=None, error_no=None, **kwargs) -> None:
        """Log a message at the error level.

        These messages will always be shown in the console and the log file.
        """
        if not self.log:
            self._logging_not_configured()

        if not self.log.isEnabledFor(40):
            return

        self.log.log(40, self.format_log_line(msg, context, error_no), *args, **kwargs)

    def format_log_line(self, msg, context, error_no) -> str:
        """Return a formatted log line with log link and context."""
        if error_no:
            error_slug = "Log-{}-{}".format(self.log.name, error_no)
            error_url = log_url.format(error_slug)
        if error_no and context:
            return "{} Context: {} Log Code: {} ({})".format(msg, context, error_slug, error_url)
        elif context:
            return "{} Context: {} ".format(msg, context)
        elif error_no:
            return "{} Log Code: {} ({})".format(msg, error_slug, error_url)
        else:
            return msg

    def raise_config_error(self, msg, error_no, *, context=None):
        """Raise a ConfigFileError exception."""
        raise ConfigFileError(msg, error_no, self.log.name, context)

    def ignorable_runtime_exception(self, msg: str) -> None:
        """Handle ignorable runtime exception.

        During development or tests raise an exception for easier debugging. Log an error during production.
        """
        if self._debug_to_console:
            raise RuntimeError(msg)
        else:
            self.error_log(msg)

    def _logging_not_configured(self) -> None:
        raise RuntimeError(
            "Logging has not been configured for the {} module. You must call "
            "configure_logging() before you can post a log message".
            format(self))
