"""
system.py

Contains the following components:
- The system timer and periodic timers
- Task handling
- Event handing

"""

import logging

HZ = None
secs_per_tick = None
tick = 0

class Timing(object):
    """System timing object.

    This object manages timing for the whole system.  Only one of these
    objects should exist.  By convention it is called 'timing'.

    The timing keeps the current time in 'time' and a set of Timer
    objects.
    """

    def __init__(self, machine):

        self.timers = set()
        self.log = logging.getLogger("Timing")
        self.machine = machine

    def configure(self, dev=None, HZ=50):
        # Do the config at the platform level since some hardware handles the
        # timers and others don't.
        self.machine.platform.timer_config(HZ)

    def add(self, timer):
        timer.wakeup = tick + timer.frequency
        self.timers.add(timer)

    def remove(self, timer):
        self.timers.remove(timer)

    def timer_tick(self):
        global tick
        tick += 1
        for timer in self.timers:
            if timer.wakeup and timer.wakeup <= tick:
                timer.call()
                if timer.frequency:
                    timer.wakeup += timer.frequency
                else:
                    timer.wakeup = None

    @staticmethod
    def msecs(ms):
        """ converts the number of msecs to ticks (based on the machine HZ)"""
        return int(ms / secs_per_tick / 1000)

    @staticmethod
    def secs(s):
        return int(s / secs_per_tick)

    @staticmethod
    def time_to_ticks(time):
        """ converts a string of real-world time into game ticks. Example
        inputs:

        200ms
        2s

        If no "s" or "ms" is provided, we assume "Seconds"

        returns an integer of game ticks
        """

        time = str(time).upper()
        if time.endswith("ms") or time.endswith("msec"):
            time = ''.join(i for i in time if not i.isalpha())
            return Timing.msecs(float(time))
        else:
            time = ''.join(i for i in time if not i.isalpha())
            return Timing.secs(float(time))


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
        # convert incoming frequency in ms to ticks
        self.frequency = frequency / 1000 * HZ

        self.log = logging.getLogger("Timer")
        self.log.debug('Creating timer for callback "%s" every %sms (every '
                         '%s ticks)', self.callback.__name__, frequency,
                         self.frequency)

    def call(self):
        self.callback(*self.args)
