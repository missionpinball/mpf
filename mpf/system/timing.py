"""Contains Timing and Timer classes"""

import logging
import time
from mpf.system.clock import Clock


class Timing(object):
    """System timing object.

    This object manages timing for the whole system.  Only one of these
    objects should exist.  By convention it is called 'timing'.

    The timing keeps the current time in 'time' and a set of Timer
    objects.
    """

    HZ = None
    """Number of ticks per second."""
    secs_per_tick = None
    """Float of how many seconds one tick takes."""
    ms_per_tick = None
    """Float of how many milliseconds one tick takes."""
    tick = 0
    """Current tick number of the machine. Starts at 0 when MPF boots and counts
    up forever until MPF ends. Used instead of real-world time for all MPF time-
    related functions.
    """

    def __init__(self, machine):

        self.timers = set()
        self.timers_to_remove = set()
        self.timers_to_add = set()
        self.log = logging.getLogger("Timing")
        self.machine = machine

        try:
            Timing.HZ = self.machine.config['timing']['hz']
        except KeyError:
            Timing.HZ = 30

        self.log.debug("Configuring system Timing for %sHz", Timing.HZ)
        Timing.secs_per_tick = 1 / float(Timing.HZ)
        Timing.ms_per_tick = 1000 * Timing.secs_per_tick

    def add(self, timer):
        timer.wakeup = Clock.get_time() + timer.frequency
        self.timers_to_add.add(timer)

    def remove(self, timer):
        self.timers_to_remove.add(timer)

    def get_next_timer(self):
        next_timer = False
        for timer in self.timers:
            if not next_timer or next_timer > timer.wakeup:
                next_timer = timer.wakeup
        return next_timer

    def timer_tick(self):
        global tick
        Timing.tick += 1
        for timer in self.timers:
            if timer.wakeup and timer.wakeup <= Clock.get_time():
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
    def string_to_secs(time_string):
        """Decodes a string of real-world time into an float of seconds.

        See 'string_to_ms' for a description of the time string.

        """

        time_string = str(time_string)

        if not any(c.isalpha() for c in time_string):
            time_string = ''.join((time_string, 's'))

        return Timing.string_to_ms(time_string) / 1000.0

    @staticmethod
    def string_to_ms(time_string):
        """Decodes a string of real-world time into an int of milliseconds.
        Example inputs:

        200ms
        2s
        None

        If no "s" or "ms" is provided, this method assumes "milliseconds."

        If time is 'None' or a string of 'None', this method returns 0.

        Returns:
            Integer. The examples listed above return 200, 2000 and 0,
            respectively
        """

        time_string = str(time_string).upper()

        if time_string.endswith('MS') or time_string.endswith('MSEC'):
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(time_string)

        elif 'D' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 86400 * 1000)

        elif 'H' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 3600 * 1000)

        elif 'M' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 60 * 1000)

        elif time_string.endswith('S') or time_string.endswith('SEC'):
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 1000)

        elif not time_string or time_string == 'NONE':
            return 0

        elif '.' in time_string:
            time_string = float(''.join(i for i in time_string if not i.isalpha()))
        else:
            time_string = ''.join(i for i in time_string if not i.isalpha())

        return int(time_string)

    @staticmethod
    def string_to_ticks(time_string):
        """Converts a string of real-world time into a float of how many machine
        ticks correspond to that amount of time.

        See 'string_to_ms' for a description of the time string.

        """
        return Timing.string_to_ms(time_string) / Timing.ms_per_tick

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
                output |= 1
                whole_num += 1
            output <<= 1

        return output

    @staticmethod
    def pwm_ms_to_byte_int(self, pwm_on, pwm_off):
        """Converts a pwm_on / pwm_off ms times to a single byte pwm mask.

        """

        total_ms = pwm_on + pwm_off

        if total_ms % 2 or total_ms > 8:
            # todo dunno what to do here.
            self.log.error("pwm_ms_to_byte error: pwm_on + pwm_off total must "
                           "be 1, 2, 4, or 8.")
            quit()

        if not pwm_on:
            return 0

        elif not pwm_off:
            return 255

        else:
            return int(pwm_on / float(pwm_on + pwm_off) * 255)


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
