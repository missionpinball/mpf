"""Contains the LogMixin class."""
import logging


class LogMixin:

    """Mixin class to add smart logging functionality to modules."""

    def configure_logging(self, logger, console_level='basic',
                          file_level='basic'):
        """Configure the logging for the module this class is mixed into.

        Args:
            logger: The string name of the logger to use
            console_level: The level of logging for the console. Valid options
                are "none", "basic", or "full".
            file_level: The level of logging for the console. Valid options
                are "none", "basic", or "full".
        """
        self.log = logging.getLogger(logger)

        self._info_to_console = False
        self._debug_to_console = False
        self._info_to_file = False
        self._debug_to_file = False

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

    def debug_log(self, msg, *args, **kwargs):
        """Log a message at the debug level.

        Note that whether this message shows up in the console or log file is
        controlled by the settings used with configure_logging().
        """
        if not hasattr(self, 'log'):
            self._logging_not_configured()

        if self._debug_to_console:
            self.log.log(20, msg, *args, **kwargs)
        elif self._debug_to_file:
            self.log.log(11, msg, *args, **kwargs)

    def info_log(self, msg, *args, **kwargs):
        """Log a message at the info level.

        Whether this message shows up in the console or log file is controlled
        by the settings used with configure_logging().
        """
        if not self.log:
            self._logging_not_configured()

        if self._info_to_console or self._debug_to_console:
            self.log.log(20, msg, *args, **kwargs)
        elif self._info_to_file or self._debug_to_file:
            self.log.log(11, msg, *args, **kwargs)

    def warning_log(self, msg, *args, **kwargs):
        """Log a message at the warning level.

        These messages will always be shown in the console and the log file.
        """
        if not self.log:
            self._logging_not_configured()

        self.log.log(30, 'WARNING: {}'.format(msg), *args, **kwargs)

    def error_log(self, msg, *args, **kwargs):
        """Log a message at the error level.

        These messages will always be shown in the console and the log file.
        """
        if not self.log:
            self._logging_not_configured()

        self.log.log(40, 'ERROR: {}'.format(msg), *args, **kwargs)

    def _logging_not_configured(self):
        raise RuntimeError(
            "Logging has not been configured for the {} module. You must call "
            "configure_logging() before you can post a log message".
            format(self))
