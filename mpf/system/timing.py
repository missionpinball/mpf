"""Contains Timing and Timer classes"""
# timing.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from math import ceil
import time


class Timing(object):
    """System timing object.

    This object manages timing for the whole system.  Only one of these
    objects should exist.  By convention it is called 'timing'.

    The timing keeps the current time in 'time' and a set of Timer
    objects.
    """

    HZ = None
    secs_per_tick = None
    tick = 0

    def __init__(self, machine):

        self.timers = set()
        self.log = logging.getLogger("Timing")
        self.machine = machine

    def configure(self, dev=None, HZ=50):
        self.log.info("Configuring system Timing for %sHz", HZ)
        Timing.HZ = HZ
        Timing.secs_per_tick = 1 / float(HZ)

    def add(self, timer):
        timer.wakeup = time.clock() + timer.frequency
        self.timers.add(timer)

    def remove(self, timer):
        self.timers.remove(timer)

    def timer_tick(self):
        global tick
        Timing.tick += 1
        #self.log.debug("t:%s", Timing.tick)
        for timer in self.timers:
            if timer.wakeup and timer.wakeup <= time.clock():
                timer.call()
                if timer.frequency:
                    timer.wakeup += timer.frequency
                else:
                    timer.wakeup = None

    @staticmethod
    def secs(s):
        return int(s * 1000)

    @staticmethod
    def string_to_ms(time):
        """Converts a string of real-world time into int of ms. Example
        inputs:

        200ms
        2s

        If no "s" or "ms" is provided, we assume "milliseconds"

        returns an integer 200 or 2000, respectively
        """
        time = str(time).upper()

        if time.endswith("MS") or time.endswith("MSEC"):
            time = ''.join(i for i in time if not i.isalpha())
            return int(time)

        elif time.endswith("S") or time.endswith("SEC"):
            time = ''.join(i for i in time if not i.isalpha())
            return int(float(time) * 1000)

        else:
            time = ''.join(i for i in time if not i.isalpha())
            return int(time)


class Timer(object):
    """Periodic timer object.

    A timer defines a callable plus a frequency (in ms) at which it should be
    called. The frequency can be set to None so that the timer is not enabled,
    but it still exists.
    """
    def __init__(self, callback, args=tuple(), frequency=None):
        self.callback = callback
        self.args = args
        self.wakeup = None
        self.frequency = frequency

        self.log = logging.getLogger("Timer")
        self.log.debug('Creating timer for callback "%s" every %sms (every '
                         '%sms)', self.callback.__name__, frequency,
                         self.frequency)

    def call(self):
        self.callback(*self.args)

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
