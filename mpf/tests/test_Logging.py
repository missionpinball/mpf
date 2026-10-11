import unittest
import logging
from logging.handlers import BufferingHandler
from mpf.core.logging import LogMixin
from mpf.commands.game import ConsoleCustomLevelFilter, FileCustomLevelFilter

class MockedLogMixin(LogMixin):
    pass

class TestLoggingFilterPipeline(unittest.TestCase):

    """Validates that Console and File filters drop/keep records correctly."""

    def setUp(self):
        # Clear out existing handlers for isolation
        self.logger = logging.getLogger("mpf_test_pipeline")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        self.logger.propagate = False

        # mock console and file loggers
        self.console_buffer = BufferingHandler(capacity=100)
        self.console_buffer.addFilter(ConsoleCustomLevelFilter())
        self.logger.addHandler(self.console_buffer)

        self.file_buffer = BufferingHandler(capacity=100)
        self.file_buffer.addFilter(FileCustomLevelFilter())
        self.logger.addHandler(self.file_buffer)

        self.mixin = MockedLogMixin()
        self.mixin.log = self.logger

    def tearDown(self):
        self.logger.handlers = []

    def test_pipeline_when_both_active(self):
        """When both are active, level 10/20 should log to both channels."""
        self.mixin._info_to_console = True
        self.mixin._info_to_file = True
        self.mixin._debug_to_console = True
        self.mixin._debug_to_file = True

        self.mixin.info_log("Shared Info Msg")
        self.mixin.debug_log("Shared Debug Msg")

        self.assertEqual(len(self.console_buffer.buffer), 2)
        self.assertEqual(len(self.file_buffer.buffer), 2)
        self.assertEqual(self.console_buffer.buffer[0].getMessage(), "Shared Info Msg")
        self.assertEqual(self.file_buffer.buffer[0].getMessage(), "Shared Info Msg")

    def test_pipeline_when_console_only(self):
        """When console-only is active, level 12/22 must be ignored by file filter."""
        self.mixin._info_to_console = True
        self.mixin._info_to_file = False
        self.mixin._debug_to_console = True
        self.mixin._debug_to_file = False

        self.mixin.info_log("Console Only Info")
        self.mixin.debug_log("Console Only Debug")

        self.assertEqual(len(self.console_buffer.buffer), 2)
        self.assertEqual(len(self.file_buffer.buffer), 0)

    def test_pipeline_when_file_only(self):
        """When file-only is active, level 11/21 must be ignored by console filter."""
        self.mixin._info_to_console = False
        self.mixin._info_to_file = True
        self.mixin._debug_to_console = False
        self.mixin._debug_to_file = True

        self.mixin.info_log("File Only Info")
        self.mixin.debug_log("File Only Debug")

        self.assertEqual(len(self.file_buffer.buffer), 2)
        self.assertEqual(len(self.console_buffer.buffer), 0)
