'''
Clock tests
===========
'''

import unittest
from mpf.core.clock import ClockBase
from functools import partial

counter = 0


def callback(dt):
    global counter
    counter += 1


class ClockTestCase(unittest.TestCase):

    def setUp(self):
        global counter
        counter = 0
        self.clock = ClockBase()
        self.clock._events = [[] for i in range(256)]
        self.callback_order = []

    def callback1(self, number, dt):
        self.callback_order.append(number)

    def test_schedule_once(self):
        self.clock.schedule_once(callback)
        self.clock.tick()
        self.assertEqual(counter, 1)

    def test_schedule_once_twice(self):
        self.clock.schedule_once(callback)
        self.clock.schedule_once(callback)
        self.clock.tick()
        self.assertEqual(counter, 2)

    def test_schedule_once_draw_after(self):
        self.clock.schedule_once(callback, 0)
        self.clock.tick_draw()
        self.assertEqual(counter, 0)
        self.clock.tick()
        self.assertEqual(counter, 1)

    def test_schedule_once_draw_before(self):
        self.clock.schedule_once(callback, -1)
        self.clock.tick_draw()
        self.assertEqual(counter, 1)
        self.clock.tick()
        self.assertEqual(counter, 1)

    def test_unschedule(self):
        self.clock.schedule_once(callback)
        self.clock.unschedule(callback)
        self.clock.tick()
        self.assertEqual(counter, 0)

    def test_unschedule_after_tick(self):
        self.clock.schedule_once(callback, 5.)
        self.clock.tick()
        self.clock.unschedule(callback)
        self.clock.tick()
        self.assertEqual(counter, 0)

    def test_unschedule_draw(self):
        self.clock.schedule_once(callback, 0)
        self.clock.tick_draw()
        self.assertEqual(counter, 0)
        self.clock.unschedule(callback)
        self.clock.tick()
        self.assertEqual(counter, 0)

    def test_callback_order(self):
        # Create two callbacks that should be called in the same tick, however the one
        # added second should be called first based on the timeout value.
        self.clock.schedule_once(partial(self.callback1, 2), timeout=0.00002)
        self.clock.schedule_once(partial(self.callback1, 1), timeout=0.00001)
        self.clock.tick()
        self.assertTrue(self.clock.frametime >= 0.0002)
        self.assertTrue(self.callback_order[0] == 1 and self.callback_order[1] == 2)
        self.callback_order.clear()

        # Create two callbacks with the same time and the same priority.  The first one
        # added should be called first.
        self.clock.schedule_once(partial(self.callback1, 1))
        self.clock.schedule_once(partial(self.callback1, 2))
        self.clock.tick()
        self.assertTrue(self.callback_order[0] == 1 and self.callback_order[1] == 2)
        self.callback_order.clear()

        # Create two callbacks with the same time and different priorities.  The highest
        # priority should be called first.
        self.clock.schedule_once(partial(self.callback1, 2), 0, 10)
        self.clock.schedule_once(partial(self.callback1, 1), 0, 100)
        self.clock.tick()
        self.assertTrue(self.callback_order[0] == 1 and self.callback_order[1] == 2)
        self.callback_order.clear()
