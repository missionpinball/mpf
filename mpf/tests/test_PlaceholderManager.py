"""Test placeholders."""
import unittest
from unittest.mock import MagicMock

from mpf.core.placeholder_manager import PlaceholderManager


class TestPlaceholderManager(unittest.TestCase):

    def test_operations(self):
        mock_machine = MagicMock()
        p = PlaceholderManager(mock_machine)

        # test mod operator
        template = p.build_int_template("a % 7", None)
        self.assertEqual(3, template.evaluate({"a": 10}))
