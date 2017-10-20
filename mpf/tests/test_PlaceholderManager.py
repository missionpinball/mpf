"""Test placeholders."""
import unittest
from unittest.mock import MagicMock

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase

from mpf.core.placeholder_manager import PlaceholderManager


class TestPlaceholderManager(unittest.TestCase):

    def test_operations(self):
        mock_machine = MagicMock()
        p = PlaceholderManager(mock_machine)

        # test mod operator
        template = p.build_int_template("a % 7", None)
        self.assertEqual(3, template.evaluate({"a": 10}))


class TestPlaceholderManagerWithMachine(MpfFakeGameTestCase):

    def test_subscribe(self):
        self.start_game()
        template = self.machine.placeholder_manager.build_int_template(
            "machine.a + current_player.b", 0)

        value, subscription = template.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(0, value)

        self.machine.set_machine_var("c", 3)
        self.advance_time_and_run()
        self.assertFalse(subscription.done())

        self.machine.set_machine_var("a", 3)
        self.advance_time_and_run()
        self.assertTrue(subscription.done())

        value, subscription = template.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(3, value)

        self.machine.game.player.a = 7
        self.advance_time_and_run()
        self.assertFalse(subscription.done())

        self.machine.game.player.b = 7
        self.advance_time_and_run()
        self.assertTrue(subscription.done())

        value, subscription = template.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(10, value)

        self.machine.game.player.b = 8
        self.advance_time_and_run()
