"""Test placeholders."""
import unittest
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from unittest.mock import MagicMock

from mpf.core.placeholder_manager import PlaceholderManager


class TestPlaceholderManager(unittest.TestCase):

    def test_operations(self):
        mock_machine = MagicMock()
        p = PlaceholderManager(mock_machine)

        # test mod operator
        template = p.build_int_template("a % 7", None)
        self.assertEqual(3, template.evaluate({"a": 10}))

class TestPlaceholderInGame(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/placeholder/'

    def get_platform(self):
        return 'smart_virtual'

    def test_player_vars_and_conditionals(self):
        self.start_game()
        self.assertPlayerVarEqual(4, "test_int")
        self.assertPlayerVarEqual("Test", "test_str")

        self.mock_event("test_yes")
        self.mock_event("test_no")
        self.post_event("test_conditional")

        self.assertEventCalled("test_yes")
        self.assertEventNotCalled("test_no")

