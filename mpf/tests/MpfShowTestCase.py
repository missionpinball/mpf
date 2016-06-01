"""Test shows in MPF."""
from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class MpfShowTestCase(MpfTestCase):

    """Testcase for shows in game."""

    def assertShowRunning(self, show_name):
        for running_show in self.machine.show_controller.running_shows:
            if self.machine.shows[show_name] == running_show.show:
                return

        self.fail("Show {} not running".format(show_name))

    def assertShowNotRunning(self, show_name):
        for running_show in self.machine.show_controller.running_shows:
            if self.machine.shows[show_name] == running_show.show:
                self.fail("Show {} should not be running".format(show_name))