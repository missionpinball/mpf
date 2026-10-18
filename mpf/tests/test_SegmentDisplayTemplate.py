"""Regression tests for formatting fields containing integrated punctuation."""
import asyncio
import unittest
from unittest.mock import MagicMock

from mpf.core.placeholder_manager import MpfFormatter, PlaceholderManager, TextTemplate
from mpf.devices.segment_display.segment_display_template import SegmentDisplayFormatter, SegmentDisplayTextTemplate
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText
from mpf.devices.segment_display.transitions import NoTransition, TransitionRunner


class TestSegmentDisplayTemplate(unittest.TestCase):

    def test_numeric_alignment(self):
        formatter = SegmentDisplayFormatter(None, {}, False, True, False, True)
        cases = [
            (1234, '8,d', '    1234'),
            (1234, '<8,d', '1234    '),
            (1234, '^8,d', '  1234  '),
            (1234, '08,d', '00001234'),
            (1234, '008,d', '00001234'),
            (1234, '>08,d', '00001234'),
            (-1234, '08,d', '-0001234'),
            (1234, '+08,d', '+0001234'),
            (1234.5, '<8,.1f', '12345   '),
            (123456789, '8,d', '123456789'),
        ]
        for value, spec, expected in cases:
            with self.subTest(value=value, spec=spec):
                text = formatter.format_field(value, spec)
                cells = SegmentDisplayText.from_str(text, len(expected), True, False, True)
                self.assertEqual(expected, ''.join(chr(char.char_code) for char in cells))
                self.assertTrue(any(char.dot for char in cells))

    def test_punctuation_settings_and_fill(self):
        cases = [
            (False, False, False, 1234, '<8,d', '1,234   '),
            (True, False, False, 1234, '<8,d', '1,234   '),
            (False, True, False, 1234, '<8,d', '1,234    '),
            (False, False, True, 1234, '<8,d', '1,234    '),
            (True, False, False, 12.5, '<6.1f', '12.5   '),
            (True, False, True, 1234, '.<8,d', '1,234...'),
            (True, False, True, 1234, '*<8,d', '1,234****'),
            (True, False, True, None, '8,d', '       0'),
        ]
        for dots, commas, dots_for_commas, value, spec, expected in cases:
            with self.subTest(settings=(dots, commas, dots_for_commas), value=value, spec=spec):
                formatter = SegmentDisplayFormatter(None, {}, False, dots, commas, dots_for_commas)
                self.assertEqual(expected, formatter.format_field(value, spec))

    def test_shared_formatter_unchanged(self):
        self.assertEqual('1,234   ', MpfFormatter(None, {}, False).format_field(1234, '<8,d'))

    def test_transition_formatting(self):
        machine = MagicMock()
        machine.placeholder_manager.build_raw_template.return_value.evaluate.return_value = 1234
        runner = TransitionRunner(machine, NoTransition(8, True, False, True, {}), '', '{score:<8,d}')
        cells = next(runner)
        self.assertEqual('1234    ', ''.join(chr(char.char_code) for char in cells))
        self.assertTrue(cells[0].dot)

    def test_multiple_fields_and_nested_width(self):
        machine = MagicMock()
        machine.placeholder_manager = PlaceholderManager(machine)
        template = SegmentDisplayTextTemplate(machine, '{score:<{width},d}|{score:08,d}', True, False, True)
        self.assertEqual('1,234    |00,001,234', template.evaluate({'score': 1234, 'width': 8}))
        ordinary = TextTemplate(machine, '{score:<8,d}')
        self.assertEqual('1,234   ', ordinary.evaluate({'score': 1234}))
        unintegrated = SegmentDisplayTextTemplate(machine, '{score:<8,d}', False, False, False)
        self.assertEqual('1,234   ', unintegrated.evaluate({'score': 1234}))


class TestSegmentDisplayTemplateSubscription(unittest.IsolatedAsyncioTestCase):

    async def test_subscribed_evaluation(self):
        machine = MagicMock()
        placeholder = machine.placeholder_manager.build_raw_template.return_value
        changed = asyncio.get_running_loop().create_future()
        placeholder.evaluate_and_subscribe.return_value = (1234, changed)
        template = SegmentDisplayTextTemplate(machine, '{score:<8,d}', True, False, True)
        text, future = template.evaluate_and_subscribe({})
        self.assertEqual('1,234    ', text)
        changed.set_result(None)
        await future
        placeholder.evaluate_and_subscribe.return_value = (12345, asyncio.get_running_loop().create_future())
        text, future = template.evaluate_and_subscribe({})
        self.assertEqual('12,345   ', text)
        future.cancel()
