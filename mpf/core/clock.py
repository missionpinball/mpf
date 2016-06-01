"""MPF clock and main loop."""

from operator import attrgetter
from sys import platform
from functools import partial

import itertools
import time
import logging

import select

# pylint: disable-msg=anomalous-backslash-in-string
"""
Clock object
============

The :class:`Clock` object allows you to schedule a function call in the
future; once or repeatedly at specified intervals. It's heavily based on
Kivy's Clock object. (Almost 100% identical.) An instance of the clock is
available in MPF set `self.machine.clock`.

You can get the time elapsed between the scheduling and the calling of the
callback via the `dt` argument::

    # dt means delta-time
    def my_callback(self, dt):
        pass

    # call my_callback every 0.5 seconds
    self.machine.clock.schedule_interval(my_callback, 0.5)

    # call my_callback in 5 seconds
    self.machine.clock..schedule_once(my_callback, 5)

    # call my_callback as soon as possible (usually next frame.)
    self.machine.clock..schedule_once(my_callback)

.. note::

    If the callback returns False, the schedule will be removed.

If you want to schedule a function to call with default arguments, you can use
the `functools.partial
<http://docs.python.org/library/functools.html#functools.partial>`_ python
module::

    from functools import partial

    def my_callback(value, key, *largs):
        pass

    self.machine.clock.schedule_interval(partial(my_callback, 'my value', 'my key'), 0.5)

Conversely, if you want to schedule a function that doesn't accept the dt
argument, you can use a `lambda
<http://docs.python.org/2/reference/expressions.html#lambda>`_ expression
to write a short function that does accept dt. For Example::

    def no_args_func():
        print("I accept no arguments, so don't schedule me in the clock")

    self.machine.clock..schedule_once(lambda dt: no_args_func(), 0.5)

.. note::

    You cannot unschedule an anonymous function unless you keep a
    reference to it. It's better to add \*args to your function
    definition so that it can be called with an arbitrary number of
    parameters.

.. important::

    The callback is weak-referenced: you are responsible for keeping a
    reference to your original object/callback. If you don't keep a
    reference, the ClockBase will never execute your callback. For
    example::

        class Foo(object):
            def start(self):
                self.machine.clock..schedule_interval(self.callback, 0.5)

            def callback(self, dt):
                print('In callback')

        # A Foo object is created and the method start is called.
        # Because no reference is kept to the instance returned from Foo(),
        # the object will be collected by the Python Garbage Collector and
        # your callback will be never called.
        Foo().start()

        # So you should do the following and keep a reference to the instance
        # of foo until you don't need it anymore!
        foo = Foo()
        foo.start()


.. _schedule-before-frame:

Schedule before frame
---------------------

Sometimes you need to schedule a callback BEFORE the next frame. Starting
from 1.0.5, you can use a timeout of -1::

    self.machine.clock.schedule_once(my_callback, 0) # call after the next frame
    self.machine.clock.schedule_once(my_callback, -1) # call before the next frame

The Clock will execute all the callbacks with a timeout of -1 before the
next frame even if you add a new callback with -1 from a running
callback. However, :class:`Clock` has an iteration limit for these
callbacks: it defaults to 10.

If you schedule a callback that schedules a callback that schedules a .. etc
more than 10 times, it will leave the loop and send a warning to the console,
then continue after the next frame. This is implemented to prevent bugs from
hanging or crashing the application.

If you need to increase the limit, set the :attr:`max_iteration` property::

    self.machine.clock.max_iteration = 20

Threading
----------

Often, other threads are used to schedule callbacks with MPF's main thread
using :class:`ClockBase`. Therefore, it's important to know what is thread safe
and what isn't.

All the :class:`ClockBase` and :class:`ClockEvent` methods are safe with
respect to MPF's thread. That is, it's always safe to call these methods
from a single thread that is not the main thread. However, there are no
guarantees as to the order in which these callbacks will be executed.

"""


"""
---------------------
MPF v0.30
This file was adapted from Kivy for use in MPF.  The following changes have
been made for use in MPF:
    1) Support proper event callback order in a frame based on scheduled callback
       time (earliest first), priority (highest first), and finally the order
       in which the callback was added to the clock. This involved adding
       triggered events to a priority queue and then executing all the callbacks
       in the queue during each frame.
    2) The 5ms look-ahead for activating events has been removed.
    3) next_event_time and last_event_time properties have been added.
    4) Clock is not used as a global singleton in MPF, but rather as an
       instantiated object.  Multiple clock objects could be used in a single
       program if desired.
    5) max_fps is now a parameter in the Clock constructor (defaults to 60) that
       controls the maximum speed at which the MPF main loop/clock runs.

MPF v0.31
    1) Clock is now tickless. No more fps
    2) Clock can wait on sockets
"""

__all__ = ('ClockBase', 'ClockEvent')


_default_time = time.perf_counter
'''A clock with the highest available resolution. '''

try:
    # pylint: disable-msg=wrong-import-position
    # pylint: disable-msg=wrong-import-order
    import ctypes
    if platform in ('win32', 'cygwin'):
        # Win32 Sleep function is only 10-millisecond resolution, so
        # instead use a waitable timer object, which has up to
        # 100-nanosecond resolution (hardware and implementation
        # dependent, of course).

        _kernel32 = ctypes.windll.kernel32

        class _ClockBase(object):
            def __init__(self):
                self._timer = _kernel32.CreateWaitableTimerA(None, True, None)

            def usleep(self, microseconds):
                """Usleep on Windows.

                Args:
                    microseconds: time to sleep in us
                """
                delay = ctypes.c_longlong(int(-microseconds * 10))
                _kernel32.SetWaitableTimer(
                    self._timer, ctypes.byref(delay), 0,
                    ctypes.c_void_p(), ctypes.c_void_p(), False)
                _kernel32.WaitForSingleObject(self._timer, 0xffffffff)
    else:
        if platform == 'darwin':
            _libc = ctypes.CDLL('libc.dylib')
        else:
            # pylint: disable-msg=wrong-import-position
            # pylint: disable-msg=wrong-import-order
            from ctypes.util import find_library
            _libc = ctypes.CDLL(find_library('c'), use_errno=True)

            def _libc_clock_gettime_wrapper():
                from os import strerror

                class StructTv(ctypes.Structure):

                    """Struct for linux time."""

                    _fields_ = [('tv_sec', ctypes.c_long),
                                ('tv_usec', ctypes.c_long)]

                _clock_gettime = _libc.clock_gettime
                _clock_gettime.argtypes = [ctypes.c_long,
                                           ctypes.POINTER(StructTv)]

                if 'linux' in platform:
                    _clockid = 4  # CLOCK_MONOTONIC_RAW (Linux specific)
                else:
                    _clockid = 1  # CLOCK_MONOTONIC

                tv = StructTv()

                def _time():
                    if _clock_gettime(ctypes.c_long(_clockid),
                                      ctypes.pointer(tv)) != 0:
                        _ernno = ctypes.get_errno()
                        raise OSError(_ernno, strerror(_ernno))
                    return tv.tv_sec + (tv.tv_usec * 0.000000001)

                return _time

            _default_time = _libc_clock_gettime_wrapper()

        _libc.usleep.argtypes = [ctypes.c_ulong]
        _libc_usleep = _libc.usleep

        class _ClockBase(object):
            @classmethod
            def usleep(cls, microseconds):
                """Linux usleep function.

                Args:
                    microseconds: time to sleep in us
                """
                _libc_usleep(int(microseconds))

except (OSError, ImportError, AttributeError):
    # ImportError: ctypes is not available on python-for-android.
    # AttributeError: ctypes is now available on python-for-android, but
    #   "undefined symbol: clock_gettime". CF #3797
    # OSError: if the libc cannot be readed (like with buildbot: invalid ELF
    # header)

    _default_sleep = time.sleep

    class _ClockBase(object):
        @classmethod
        def usleep(cls, microseconds):
            """Default fallback usleep function.

            Args:
                microseconds: time to sleep in us
            """
            _default_sleep(microseconds / 1000000.)


# pylint: disable-msg=too-many-instance-attributes
class ClockEvent(object):

    """A class that describes a callback scheduled with kivy's :attr:`Clock`.

    This class is never created by the user; instead, kivy creates and returns
    an instance of this class when scheduling a callback.
    .. warning::
        Most of the methods of this class are internal and can change without
        notice. The only exception are the :meth:`cancel` and
        :meth:`__call__` methods.
    """

    __slots__ = ('clock', 'id', 'loop', 'callback', 'timeout',
                 '_last_dt', '_next_event_time', '_last_event_time', '_dt',
                 '_priority', '_callback_cancelled')

    # pylint: disable-msg=too-many-arguments
    def __init__(self, clock, loop, callback, timeout, starttime, priority=1):
        """Create clock event."""
        self.clock = clock
        self.id = next(clock.counter)
        self.loop = loop
        self.callback = callback
        self.timeout = timeout
        self._last_dt = starttime
        self._next_event_time = starttime + timeout
        self._last_event_time = 0
        self._dt = 0.
        self._priority = priority
        self._callback_cancelled = False
        clock.ordered_events.append(self)

    def get_callback(self):
        """Return the callback."""
        callback = self.callback
        if callback is not None:
            return callback
        return None

    @property
    def next_event_time(self):
        """Return the next time this event will fire."""
        return self._next_event_time

    @property
    def last_event_time(self):
        """Return the last time the event fired."""
        return self._last_event_time

    @property
    def priority(self):
        """Return priority."""
        return self._priority

    @property
    def callback_cancelled(self):
        """Return if callback is canceled."""
        return self._callback_cancelled

    def cancel(self):
        """Cancel the callback if it was scheduled to be called."""
        try:
            self.clock.ordered_events.remove(self)
        except ValueError:
            pass

        self._callback_cancelled = True

    def tick(self, curtime, remove):
        """Call the callback if time is due.

        Args:
            curtime: current time
            remove: callback to remove event
        """
        # Is it time to execute the callback (did timeout occur)?  The
        # decision is easy if this event's timeout is 0 or -1 as it
        # should be called every time.
        if self.timeout > 0 and curtime < self._next_event_time:
            return True

        # calculate current time-diff for this event
        self._dt = curtime - self._last_dt
        self._last_dt = curtime
        loop = self.loop

        if self.timeout > 0:
            self._last_event_time = self._next_event_time
            self._next_event_time += self.timeout
        else:
            self._last_event_time = curtime
            self._next_event_time = curtime

        # get the callback
        callback = self.get_callback()
        if callback is None:
            try:
                remove(self)
            except ValueError:
                pass
            return False

        # Make sure the callback will be called by resetting its cancelled flag
        self._callback_cancelled = False

        # Do not actually call the callback here, instead add it to the clock
        # frame callback queue where it will be processed after all events are processed
        # for the frame.  The callback queue is prioritized by callback time and then
        # event priority.
        self.clock.add_event_to_frame_callbacks(self)

        if not loop:
            try:
                remove(self)
            except ValueError:
                pass

    def __repr__(self):
        """Return str representation."""
        return '<ClockEvent callback=%r>' % self.get_callback()


class ClockBase(_ClockBase):

    """A clock object with event support."""

    __slots__ = ('_dt', '_last_fps_tick', '_last_tick', '_fps', '_rfps',
                 '_start_tick', '_fps_counter', '_rfps_counter', 'ordered_events',
                 '_frame_callbacks', '_frames', '_frames_displayed',
                 '_log', 'read_sockets')

    counter = itertools.count()

    def __init__(self):
        """Initialise clock."""
        super(ClockBase, self).__init__()

        self._dt = 0.0001
        self._start_tick = self._last_tick = self.time()
        self._fps = 0
        self._rfps = 0
        self._fps_counter = 0
        self._rfps_counter = 0
        self._last_fps_tick = None
        self._frames = 0
        self._frames_displayed = 0
        self.ordered_events = []
        self.read_sockets = {}
        self._frame_callbacks = []
        self._log = logging.getLogger("Clock")
        self._log.debug("Starting tickless clock")

    @property
    def frametime(self):
        """Time spent between the last frame and the current frame (in seconds).

        .. versionadded:: 1.8.0
        """
        return self._dt

    @property
    def frames(self):
        """Number of internal frames from the start of the clock (not necessarily drawn).

        .. versionadded:: 1.8.0
        """
        return self._frames

    @property
    def frames_displayed(self):
        """Number of displayed frames from the start of the clock."""
        return self._frames_displayed

    def get_next_event_time(self):
        """Return the time when the next event is scheduled."""
        if not self.ordered_events:
            return False

        self.ordered_events.sort(key=attrgetter("next_event_time"), reverse=False)
        return self.ordered_events[0].next_event_time

    def _sleep_until_next_event(self):
        next_event_time = self.get_next_event_time()
        if next_event_time:
            sleeptime = next_event_time - self.time()
        else:
            sleeptime = 0.0

        # Since windows will fail when calling select without sockets we have to fall back to usleep in that case.
        if self.read_sockets:
            # handle sleep time == 0, because select would block
            if sleeptime <= 0.0:
                sleeptime = 0.00001

            read_sockets = self.read_sockets.keys()
            read_ready, _, _ = select.select(read_sockets, [], [], sleeptime)
            if read_ready:
                for socket in list(read_ready):
                    self.read_sockets[socket]()

                # prematurely exit function if we have been woken up by a socket
                return

        # make sure we sleep long enough
        if next_event_time:
            current = self.time()
            while next_event_time > current:
                sleeptime = next_event_time - current
                usleep = self.usleep
                usleep(1000000 * sleeptime)
                current = self.time()

    def tick(self):
        """Advance the clock to the next step. Must be called every frame.

        The default clock has a tick() function called by the core Kivy
        framework.
        """
        # sleep if needed
        self._sleep_until_next_event()

        # tick the current time
        current = self.time()
        self._dt = current - self._last_tick
        self._frames += 1
        self._fps_counter += 1
        self._last_tick = current

        # calculate fps things
        if self._last_fps_tick is None:
            self._last_fps_tick = current
        elif current - self._last_fps_tick > 1:
            d = float(current - self._last_fps_tick)
            self._fps = self._fps_counter / d
            self._rfps = self._rfps_counter
            self._last_fps_tick = current
            self._fps_counter = 0
            self._rfps_counter = 0

        # process event
        self._process_events()

        # now process event callbacks
        self._process_event_callbacks()

        return self._dt

    def tick_draw(self):
        """Tick the drawing counter."""
        self._rfps_counter += 1
        self._frames_displayed += 1

    def get_fps(self):
        """Get the current average FPS calculated by the clock."""
        return self._fps

    def get_rfps(self):
        """Get the current "real" FPS calculated by the clock.

        This counter reflects the real framerate displayed on the screen.
        In contrast to get_fps(), this function returns a counter of the
        number of frames, not the average of frames per second.
        """
        return self._rfps

    def get_time(self):
        """Get the last tick made by the clock."""
        return self._last_tick

    def get_boottime(self):
        """Get the time in seconds from the application start."""
        return self._last_tick - self._start_tick

    def schedule_socket_read_callback(self, socket, callback):
        """Schedule a callback when the socket is ready.

        Args:
            socket: Any type of socket which can be passed to select.
            callback: Callback to call
        """
        self.read_sockets[socket] = callback

    def unschedule_socket_read_callback(self, socket):
        """Remove a socket callback which has to be registered.

        Args:
            socket: Socket so remove.
        """
        del self.read_sockets[socket]

    def schedule_once(self, callback, timeout=0, priority=1):
        """Schedule an event in <timeout> seconds.

        If <timeout> is unspecified
        or 0, the callback will be called after the next frame is rendered.
        Args:
            callback: callback to call on timeout
            timeout: seconds to wait
            priority: priority when getting called

        Returns:
            A :class:`ClockEvent` instance.
        """
        if not callable(callback):
            raise AssertionError('callback must be a callable, got %s' % callback)
        event = ClockEvent(self, False, callback, timeout, self._last_tick, priority)

        self._log.debug("Scheduled a one-time clock callback (callback=%s, timeout=%s, priority=%s)",
                        str(callback), timeout, priority)

        return event

    def schedule_interval(self, callback, timeout, priority=1):
        """Schedule an event to be called every <timeout> seconds.

        Args:
            callback: callback to call on timeout
            timeout: period to wait
            priority: priority when getting called

        Returns:
            A :class:`ClockEvent` instance.
        """
        if not callable(callback):
            raise AssertionError('callback must be a callable, got %s' % callback)
        event = ClockEvent(self, True, callback, timeout, self._last_tick, priority)

        self._log.debug("Scheduled a recurring clock callback (callback=%s, timeout=%s, priority=%s)",
                        str(callback), timeout, priority)

        return event

    def unschedule(self, callback, all_events: bool=True):
        """Remove a previously scheduled event.

        Args:
            callback: :class:`ClockEvent` or a callable.
                If it's a :class:`ClockEvent` instance, then the callback
                associated with this event will be canceled if it is
                scheduled. If it's a callable, then the callable will be
                unscheduled if it is scheduled.
            all_events: bool
                If True and if `callback` is a callable, all instances of this
                callable will be unscheduled (i.e. if this callable was
                scheduled multiple times). Defaults to `True`.
        .. versionchanged:: 1.9.0
            The all parameter was added. Before, it behaved as if `all` was
            `True`.
        """
        if isinstance(callback, ClockEvent):
            callback.cancel()
        else:
            if all_events:
                for ev in self.ordered_events[:]:
                    if ev.get_callback() == callback:
                        ev.cancel()
            else:
                for ev in self.ordered_events[:]:
                    if ev.get_callback() == callback:
                        ev.cancel()
                        break

    def _process_events(self):
        if not self.ordered_events:
            return
        self.ordered_events.sort(key=attrgetter("next_event_time"), reverse=False)
        for event in list(self.ordered_events):
            if event.next_event_time > self._last_tick:
                break
            remove = self.ordered_events.remove
            # event may be already removed from original list
            if not event.callback_cancelled:
                event.tick(self._last_tick, remove)

    def add_event_to_frame_callbacks(self, event):
        """Add an event to the priority queue whose callback will be called in the current frame.

        Args:
            event: The event whose callback will be called (in priority order)
                during the current frame.
        """
        self._frame_callbacks.append((event.last_event_time, -event.priority, event.id, event))

    def _process_event_callbacks(self):
        """Process event callbacks that were triggered to be called in the current frame."""
        for event_obj in sorted(self._frame_callbacks):
            event = event_obj[3]
            # Call the callback if the event has not been cancelled during the current frame
            if not event.callback_cancelled:
                callback = event.get_callback()
                if callback:
                    ret = callback(self.frametime)
                else:
                    ret = False

                # if the user returns False explicitly, remove the event
                if event.loop and ret is False:
                    event.cancel()

        self._frame_callbacks = []

    time = staticmethod(partial(_default_time))

ClockBase.time.__doc__ = '''Proxy method for :func:`~kivy.compat.clock`. '''
