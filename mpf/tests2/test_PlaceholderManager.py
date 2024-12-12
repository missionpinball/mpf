"""Test placeholders."""
import unittest
from unittest.mock import MagicMock

from mpf.exceptions.config_file_error import ConfigFileError
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase

from mpf.core.placeholder_manager import PlaceholderManager, BoolTemplate, TextTemplate


class TestPlaceholderManager(unittest.TestCase):

    def test_operations(self):
        mock_machine = MagicMock()
        p = PlaceholderManager(mock_machine)

        # test mod operator
        template = p.build_int_template("a % 7", None)
        self.assertEqual(3, template.evaluate({"a": 10}))

        # test "true" and "false"
        template = p.build_int_template("a == true", None)
        with self.assertRaises(ConfigFileError):
            self.assertFalse(False, template.evaluate({"a": True}))

    def test_conditionals(self):
        mock_machine = MagicMock()
        p = PlaceholderManager(mock_machine)

        # test no conditions or numbers
        d = p.parse_conditional_template("test_string")
        self.assertEqual(d.name, "test_string")
        self.assertIsNone(d.condition)
        self.assertIsNone(d.number)
        # test number with pipe
        d = p.parse_conditional_template("test_string|12")
        self.assertEqual(d.name, "test_string")
        self.assertIsNone(d.condition)
        self.assertEqual(d.number, "12")
        # test number with colon
        d = p.parse_conditional_template("test_string:21")
        self.assertEqual(d.name, "test_string")
        self.assertIsNone(d.condition)
        self.assertEqual(d.number, "21")
        # test conditional event
        d = p.parse_conditional_template("test_string{somecondition<1}")
        self.assertEqual(d.name, "test_string")
        self.assertIsInstance(d.condition, BoolTemplate)
        self.assertIsNone(d.number)
        # test conditional event with pipe
        d = p.parse_conditional_template("test_string{somecondition<1}|32")
        self.assertEqual(d.name, "test_string")
        self.assertIsInstance(d.condition, BoolTemplate)
        self.assertEqual(d.number, "32")
        # test conditional event with colon
        d = p.parse_conditional_template("test_string{somecondition<1}:34")
        self.assertEqual(d.name, "test_string")
        self.assertIsInstance(d.condition, BoolTemplate)
        self.assertEqual(d.number, "34")
        # test default number
        d = p.parse_conditional_template("test_string", default_number=2)
        self.assertEqual(d.name, "test_string")
        self.assertEqual(d.number, 2)
        # test number typing
        d = p.parse_conditional_template("test_string|45", default_number=1.0)
        self.assertEqual(d.number, 45)
        self.assertIsInstance(d.number, float)
        # test number without typing
        d = p.parse_conditional_template("test_string:500ms")
        self.assertEqual(d.number, "500ms")
        # test fallback on unparseable number
        d = p.parse_conditional_template("test_string|foobar", default_number=8)
        self.assertEqual(d.number, 8)

class TestPlaceholderManagerWithMachine(MpfFakeGameTestCase):

    def test_subscribe(self):
        self.start_game()
        template = self.machine.placeholder_manager.build_int_template(
            "machine.a + current_player.b", 0)

        value, subscription = template.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(0, value)

        self.machine.variables.set_machine_var("c", 3)
        self.advance_time_and_run()
        self.assertFalse(subscription.done())

        self.machine.variables.set_machine_var("a", 3)
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

    def test_player_vars(self):
        self.start_game()
        template_game = self.machine.placeholder_manager.build_int_template(
            "game.max_players", 0)
        game = template_game.evaluate([])
        self.assertEqual(4, game)
        template_game = self.machine.placeholder_manager.build_int_template(
            "game.num_players", 0)
        game = template_game.evaluate([])
        self.assertEqual(1, game)

        template_current = self.machine.placeholder_manager.build_int_template(
            "current_player.score", 0)

        template1 = self.machine.placeholder_manager.build_int_template(
            "players[0].score", 0)
        template2 = self.machine.placeholder_manager.build_int_template(
            "players[1].score", 0)

        value, subscription = template_current.evaluate_and_subscribe([])
        value1, subscription1 = template1.evaluate_and_subscribe([])
        value2, subscription2 = template2.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(0, value)
        self.assertFalse(subscription1.done())
        self.assertEqual(0, value1)
        self.assertFalse(subscription2.done())
        self.assertEqual(0, value2)

        self.machine.game.player.score += 100
        self.advance_time_and_run(.1)
        self.assertTrue(subscription.done())
        self.assertTrue(subscription1.done())
        value, subscription = template_current.evaluate_and_subscribe([])
        value1, subscription1 = template1.evaluate_and_subscribe([])
        value2, subscription2 = template2.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(100, value)
        self.assertFalse(subscription1.done())
        self.assertEqual(100, value1)
        self.assertFalse(subscription2.done())
        self.assertEqual(0, value2)

        self.add_player()
        self.advance_time_and_run(.1)
        self.assertTrue(subscription2.done())
        value, subscription = template_current.evaluate_and_subscribe([])
        value1, subscription1 = template1.evaluate_and_subscribe([])
        value2, subscription2 = template2.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(100, value)
        self.assertFalse(subscription1.done())
        self.assertEqual(100, value1)
        self.assertFalse(subscription2.done())
        self.assertEqual(0, value2)

        template_game = self.machine.placeholder_manager.build_int_template(
            "game.num_players", 0)
        game = template_game.evaluate([])
        self.assertEqual(2, game)

        self.drain_all_balls()
        self.advance_time_and_run(.1)
        value, subscription = template_current.evaluate_and_subscribe([])
        value1, subscription1 = template1.evaluate_and_subscribe([])
        value2, subscription2 = template2.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(0, value)
        self.assertFalse(subscription1.done())
        self.assertEqual(100, value1)
        self.assertFalse(subscription2.done())
        self.assertEqual(0, value2)

        self.machine.game.player.score += 42
        self.advance_time_and_run(.1)
        self.assertTrue(subscription2.done())
        value, subscription = template_current.evaluate_and_subscribe([])
        value1, subscription1 = template1.evaluate_and_subscribe([])
        value2, subscription2 = template2.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(42, value)
        self.assertFalse(subscription1.done())
        self.assertEqual(100, value1)
        self.assertFalse(subscription2.done())
        self.assertEqual(42, value2)
        self.advance_time_and_run(.1)
        self.assertFalse(subscription1.done())
        self.assertFalse(subscription2.done())

        self.machine.game.player_list[0].score += 23
        self.advance_time_and_run(.1)
        self.assertTrue(subscription1.done())
        value, subscription = template_current.evaluate_and_subscribe([])
        value1, subscription1 = template1.evaluate_and_subscribe([])
        value2, subscription2 = template2.evaluate_and_subscribe([])
        self.assertFalse(subscription.done())
        self.assertEqual(42, value)
        self.assertFalse(subscription1.done())
        self.assertEqual(123, value1)
        self.assertFalse(subscription2.done())
        self.assertEqual(42, value2)

    def testTextTemplate(self):
        t = TextTemplate(self.machine, "Number: {test:<4d}")
        self.assertEqual("Number: 7   ", t.evaluate({"test": 7}))
        self.assertEqual("Number: 0   ", t.evaluate({"test": None}))

