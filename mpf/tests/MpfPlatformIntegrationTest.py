"""Base class for MPF Platform Integration Tests."""

from mpf.core.logging import LogMixin

class MpfPlatformIntegrationTest(LogMixin):

    __slots__ = ("machine", "runner")

    def __init__(self, runner):
        self.runner = runner
        self.machine = runner.machine

    def run_test(self):
        """This method is called when it's time to run the test."""
        raise NotImplementedError