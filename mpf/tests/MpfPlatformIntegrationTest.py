"""Base class for MPF Platform Integration Tests."""

from mpf.core.logging import LogMixin

class MpfPlatformIntegrationTest(LogMixin):

    __slots__ = ("machine", "runner")

    test_start_event = "mode_attract_started"
    initial_switches = None

    def __init__(self, runner):
        super().__init__()
        self.runner = runner
        self.machine = runner.machine
        self.configure_logging(type(self).__name__)

    def run_test(self):
        """This method is called when it's time to run the test."""
        raise NotImplementedError
