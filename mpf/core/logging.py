"""Contains the LogMixin class."""
import logging

from mpf.exceptions.ConfigFileError import ConfigFileError

MYPY = False
if MYPY:   # pragma: no cover
    from logging import Logger


class LogMixin(object):

    """Mixin class to add smart logging functionality to modules."""

    unit_test = False

    def __init__(self) -> None:
        """Initialise Log Mixin."""
        self.log = None     # type: Logger
        self._info_to_console = False
        self._debug_to_console = False
        self._info_to_file = False
        self._debug_to_file = False

        logging.addLevelName(11, "INFO")
        logging.addLevelName(12, "DEBUG")
        logging.addLevelName(21, "INFO")
        logging.addLevelName(22, "DEBUG")

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

    def debug_log(self, msg: str, *args, **kwargs) -> None:
        """Log a message at the debug level.

        Note that whether this message shows up in the console or log file is
        controlled by the settings used with configure_logging().
        """
        if not hasattr(self, 'log'):
            self._logging_not_configured()

        if self._debug_to_console:
            self.log.log(22, msg, *args, **kwargs)
        elif self._debug_to_file:
            self.log.log(12, msg, *args, **kwargs)

    def info_log(self, msg: str, *args, context=None, **kwargs) -> None:
        """Log a message at the info level.

        Whether this message shows up in the console or log file is controlled
        by the settings used with configure_logging().
        """
        if not self.log:
            self._logging_not_configured()

        code = None
        if self._info_to_console or self._debug_to_console:
            code = 21
        elif self._info_to_file or self._debug_to_file:
            code = 11

        if context:
            self.log.log(code, msg + " context: " + context, *args, **kwargs)
        else:
            self.log.log(code, msg, *args, **kwargs)

    def warning_log(self, msg: str, *args, context=None, **kwargs) -> None:
        """Log a message at the warning level.

        These messages will always be shown in the console and the log file.
        """
        if not self.log:
            self._logging_not_configured()

        if context:
            self.log.log(30, 'WARNING: {} context: {}'.format(msg, context), *args, **kwargs)
        else:
            self.log.log(30, 'WARNING: {}'.format(msg), *args, **kwargs)

    def error_log(self, msg: str, *args, context=None, **kwargs) -> None:
        """Log a message at the error level.

        These messages will always be shown in the console and the log file.
        """
        if not self.log:
            self._logging_not_configured()

        if context:
            self.log.log(40, 'ERROR: {} context: {}'.format(msg, context), *args, **kwargs)
        else:
            self.log.log(40, 'ERROR: {}'.format(msg), *args, **kwargs)

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
