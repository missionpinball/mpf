"""Clock tests."""

import unittest

import asyncio

from mpf.core.clock import ClockBase
from functools import partial

counter = 0


def callback(dt):
    """Global test cb.

    Args:
        dt:
    """
    del dt
    global counter
    counter += 1


class ClockTestCase(unittest.TestCase):

    def setUp(self):
        global counter
        counter = 0
        self.clock = ClockBase()
        self.callback_order = []

    def advance_time_and_run(self, delta=1.0):
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(delay=delta))

    def callback1(self, number, dt):
        del dt
        self.callback_order.append(number)

    def test_schedule_once(self):
        self.clock.schedule_once(callback)
        self.advance_time_and_run(0.001)
        self.assertEqual(counter, 1)

    def test_schedule_once_with_timeout(self):
        self.clock.schedule_once(callback, .001)
        self.advance_time_and_run(0.002)
        self.assertEqual(counter, 1)

    def test_schedule_once_twice(self):
        self.clock.schedule_once(callback)
        self.clock.schedule_once(callback)
        self.advance_time_and_run(0.001)
        self.assertEqual(counter, 2)

    def test_unschedule(self):
        cb1 = self.clock.schedule_once(callback)
        self.clock.schedule_once(callback)
        self.clock.unschedule(cb1)
        self.advance_time_and_run(0.001)
        self.assertEqual(counter, 1)
