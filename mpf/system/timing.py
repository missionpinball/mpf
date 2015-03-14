"""Contains Timing and Timer classes"""
# timing.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
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
        self.timers_to_remove = set()
        self.timers_to_add = set()
        self.log = logging.getLogger("Timing")
        self.machine = machine

        if 'HZ' in self.machine.config['Machine']:
            Timing.HZ = self.machine.config['Machine']['HZ']
        else:
            Timing.HZ = 50

        self.log.info("Configuring system Timing for %sHz", Timing.HZ)
        Timing.secs_per_tick = 1 / float(Timing.HZ)

    def add(self, timer):
        timer.wakeup = time.time() + timer.frequency
        self.timers_to_add.add(timer)

    def remove(self, timer):
        self.timers_to_remove.add(timer)

    def timer_tick(self):
        global tick
        Timing.tick += 1
        #self.log.debug("t:%s", Timing.tick)
        for timer in self.timers:
            if timer.wakeup and timer.wakeup <= time.time():
                timer.call()
                if timer.frequency:
                    timer.wakeup += timer.frequency
                else:
                    timer.wakeup = None

        while self.timers_to_remove:
            timer = self.timers_to_remove.pop()
            if timer in self.timers:
                self.timers.remove(timer)

        for timer in self.timers_to_add:
            self.timers.add(timer)
        self.timers_to_add = set()

    @staticmethod
    def secs(s):
        return s / 1000.0

    @staticmethod
    def string_to_secs(s):
        return Timing.string_to_ms(s) / 1000.0

    @staticmethod
    def string_to_ms(time):
        """Converts a string of real-world time into int of ms. Example
        inputs:

        200ms
        2s
        None

        If no "s" or "ms" is provided, this method assumes "milliseconds."

        If time is 'None' or a string of 'None', this method returns 0.

        Returns: An integer. The examples listed above 200, 2000 and 0,
            respectively
        """

        time = str(time).upper()

        if time.endswith("MS") or time.endswith("MSEC"):
            time = ''.join(i for i in time if not i.isalpha())
            return int(time)

        elif time.endswith("S") or time.endswith("SEC"):
            time = ''.join(i for i in time if not i.isalpha())
            return int(float(time) * 1000)

        elif not time or time == 'NONE':
            return 0

        else:
            time = ''.join(i for i in time if not i.isalpha())
            return int(time)

    @staticmethod
    def int_to_pwm(ratio, length):
        """Converts a decimal between 0 and 1 to a pwm mask of whatever length
        you want.

        For example, an input ratio of .5 with a result length of 8 returns
        10101010. And input ratio of .7 with a result length of 32 returns
        11011011101101101101110110110110.

        Another way to think about this is this method converts a decimal
        percentage into the corresponding pwm mask.

        Args:
            ratio (float): A value between 0 and 1 that you want to convert.
            length (int): How many digits you want in your result.
        """

        whole_num = 0  # tracks our whole number
        output = 0  # our output mask
        count = 0  # our current count

        for _i in range(length):
            count += ratio
            if int(count) > whole_num:
                output = output | 1
                whole_num += 1
            output = output << 1

        return output


class Timer(object):
    """Periodic timer object.

    A timer defines a callable plus a frequency (in sec) at which it should be
    called. The frequency can be set to None so that the timer is not enabled,
    but it still exists.

    Args:
        callback (method): The method you want called each time this timer is
            fired.
        args (tuple): Arguments you want to pass to the callback.
        frequency (int or float): How often, in seconds, you want this timer
        to be called.
    """

    def __init__(self, callback, args=tuple(), frequency=None):
        self.callback = callback
        self.args = args
        self.wakeup = None
        self.frequency = frequency

        self.log = logging.getLogger("Timer")
        self.log.debug('Creating timer for callback "%s" every %ss',
                       self.callback.__name__, self.frequency)

    def call(self):
        self.callback(*self.args)


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

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
