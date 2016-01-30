'''
Clock tests
===========
'''

import unittest
from mpf.system.clock import ClockBase

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
