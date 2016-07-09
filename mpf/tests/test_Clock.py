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

class MockMachine:
    def get_event_loop(self):
        return asyncio.get_event_loop()


class ClockTestCase(unittest.TestCase):

    def setUp(self):
        global counter
        counter = 0
        self.clock = ClockBase(MockMachine())
        self.callback_order = []

    def advance_time_and_run(self, delta=1.0):
        task_with_timeout = asyncio.wait_for(asyncio.sleep(delay=delta),
                                             timeout=delta+1)
        asyncio.get_event_loop().run_until_complete(task_with_timeout)

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

    def test_callback_order(self):
        # Create two callbacks that should be called in the same tick, however the one
        # added second should be called first based on the timeout value.
        cb1 = self.clock.schedule_once(partial(self.callback1, 2), timeout=0.0002)
        cb2 = self.clock.schedule_once(partial(self.callback1, 1), timeout=0.0001)
        self.advance_time_and_run(0.002)
        self.assertTrue(self.callback_order[0] == 1 and self.callback_order[1] == 2)
        self.callback_order.clear()

        # Create two callbacks with the same time and the same priority.  The first one
        # added should be called first.
        self.clock.schedule_once(partial(self.callback1, 1))
        self.clock.schedule_once(partial(self.callback1, 2))
        self.advance_time_and_run(0.001)
        self.assertTrue(self.callback_order[0] == 1 and self.callback_order[1] == 2)
        self.callback_order.clear()

