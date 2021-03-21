"""Contains the LogMixin class."""
import logging
from logging import Logger

from mpf.exceptions.config_file_error import ConfigFileError
from mpf._version import log_url

MYPY = False
if MYPY:   # pragma: no cover
    from typing import NoReturn, Optional  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class LogMixin:

    """Mixin class to add smart logging functionality to modules."""

    unit_test = False

    __slots__ = ["log", "_info_to_console", "_debug_to_console", "_debug", "_info_to_file", "_debug_to_file",
                 "_info", "_url_base"]

    def __init__(self) -> None:
        """Initialise Log Mixin."""
        self.log = None     # type: Optional[Logger]
        self._info_to_console = False
        self._debug_to_console = False
        self._info_to_file = False
        self._info = False
        self._debug_to_file = False
        self._debug = False
        self._url_base = None   # type: Optional[str]

        if MYPY:
            self.machine = self.machine     # type: MachineController # noqa

        logging.addLevelName(21, "INFO")
        logging.addLevelName(11, "DEBUG")
        logging.addLevelName(22, "INFO")
        logging.addLevelName(12, "DEBUG")

    def configure_logging(self, logger: str, console_level: str = 'basic',
                          file_level: str = 'basic', url_base=None):
        """Configure logging.

        Args:
        ----
            logger: The string name of the logger to use.
            console_level: The level of logging for the console. Valid options
                are "none", "basic", or "full".
            file_level: The level of logging for the console. Valid options
                are "none", "basic", or "full".
            url_base: Base URL for docs links in exceptions.
        """
        if isinstance(url_base, str):
            self._url_base = url_base
        else:
            self._url_base = logger
        self.log = logging.getLogger(logger)
        if hasattr(self, "machine") and self.machine and self.machine.options['production']:
            return

        try:
            if console_level.lower() == 'basic':
                self._info_to_console = True
                self._info = True
            elif console_level.lower() == 'full':
                self._debug_to_console = True
                self._debug = True
        except AttributeError:
            pass

        try:
            if file_level.lower() == 'basic':
                self._info_to_file = True
                self._info = True
            elif file_level.lower() == 'full':
                self._debug_to_file = True
                self._debug = True
        except AttributeError:
            pass

        # in unit tests always log info. debug will depend on the actual settings.
        if self.unit_test:
            self._info_to_console = True
            self._info = True

    def debug_log(self, msg: str, *args, context=None, error_no=None, **kwargs) -> None:
        """Log a message at the debug level.

        Note that whether this message shows up in the console or log file is
        controlled by the settings used with configure_logging().
        """
        if not self.log:
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
            error_slug = "Log-{}-{}".format(self.log.name if self.log else "", error_no)
            error_url = log_url.format(error_slug)
        if error_no and context:
            return "{} Context: {} Log Code: {} ({})".format(msg, context, error_slug, error_url)
        if context:
            return "{} Context: {} ".format(msg, context)
        if error_no:
            return "{} Log Code: {} ({})".format(msg, error_slug, error_url)

        return msg

    def raise_config_error(self, msg, error_no, *, source_exception=None, context=None) -> "NoReturn":
        """Raise a ConfigFileError exception."""
        raise ConfigFileError(msg, error_no, self.log.name if self.log else "", context, self._url_base) \
            from source_exception

    def ignorable_runtime_exception(self, msg: str) -> None:
        """Handle ignorable runtime exception.

        During development or tests raise an exception for easier debugging. Log an error during production.
        """
        if self._debug_to_console:
            raise RuntimeError(msg)

        self.error_log(msg)

    def _logging_not_configured(self) -> "NoReturn":
        if self.machine and self.machine.is_shutting_down:
            # omit errors on shutdown
            return
        raise RuntimeError(
            "Logging has not been configured for the {} module. You must call "
            "configure_logging() before you can post a log message".
            format(self))
