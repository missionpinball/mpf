"""MPF clock and main loop."""
import asyncio
from functools import partial

from typing import Tuple, Generator

from serial_asyncio import create_serial_connection

from mpf.core.logging import LogMixin


class PeriodicTask:

    """A periodic asyncio task."""

    __slots__ = ["_canceled", "_interval", "_callback", "_loop", "_last_call"]

    def __init__(self, interval, loop, callback):
        """Initialise periodic task."""
        self._canceled = False
        self._interval = interval
        self._callback = callback
        self._loop = loop
        self._last_call = self._loop.time()
        self._schedule()

    def _schedule(self):
        if self._canceled:
            return
        self._loop.call_at(self._last_call + self._interval, self._run)

    def get_next_call_time(self):
        """Return time of next call."""
        return self._last_call + self._interval

    def _run(self):
        self._last_call = self._last_call + self._interval
        if self._canceled:
            return
        self._callback()
        self._schedule()

    def cancel(self):
        """Cancel periodic task."""
        self._canceled = True


class ClockBase(LogMixin):

    """A clock object with event support."""

    __slots__ = ["machine", "loop"]

    def __init__(self, machine=None, loop=None):
        """Initialise clock."""
        super().__init__()
        self.machine = machine

        # needed since the test clock is setup before the machine
        if machine:
            self.configure_logging(
                'Clock',
                self.machine.config['logging']['console']['clock'],
                self.machine.config['logging']['file']['clock'])
        else:
            self.configure_logging('Clock', None, None)

        self.debug_log("Starting tickless clock")
        if not loop:
            self.loop = self._create_event_loop()   # type: asyncio.BaseEventLoop
        else:
            self.loop = loop                        # type: asyncio.BaseEventLoop

    # pylint: disable-msg=no-self-use
    def _create_event_loop(self):
        try:
            import uvloop
        except ImportError:
            pass
        else:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        return asyncio.get_event_loop()

    def run(self, stop_future):
        """Run the clock."""
        return self.loop.run_until_complete(stop_future)

    def get_time(self):
        """Get the last tick made by the clock."""
        return self.loop.time()

    def start_server(self, client_connected_cb, host=None, port=None, **kwd):
        """Start a server."""
        return asyncio.start_server(client_connected_cb, host, port, loop=self.loop, **kwd)

    def open_connection(self, host=None, port=None, *,
                        limit=None, **kwds):
        """Open connection using asyncio.

        Wrapper for create_connection() returning a (reader, writer) pair.

        The reader returned is a StreamReader instance; the writer is a
        StreamWriter instance.

        The arguments are all the usual arguments to create_connection()
        except protocol_factory; most common are positional host and port,
        with various optional keyword arguments following.

        Additional optional keyword arguments are loop (to set the event loop
        instance to use) and limit (to set the buffer limit passed to the
        StreamReader).

        (If you want to customize the StreamReader and/or
        StreamReaderProtocol classes, just copy the code -- there's
        really nothing special here except some convenience.)
        """
        if not limit:
            # pylint: disable-msg=protected-access
            limit = asyncio.streams._DEFAULT_LIMIT
        return asyncio.open_connection(host=host, port=port, loop=self.loop, limit=limit, **kwds)

    @asyncio.coroutine
    def open_serial_connection(self, limit=None, **kwargs) ->\
            Generator[int, None, Tuple[asyncio.StreamReader, asyncio.StreamWriter]]:
        """Open a serial connection using asyncio.

        A wrapper for create_serial_connection() returning a (reader, writer) pair.

        The reader returned is a StreamReader instance; the writer is a StreamWriter instance.

        The arguments are all the usual arguments to Serial(). Additional
        optional keyword arguments are loop (to set the event loop instance
        to use) and limit (to set the buffer limit passed to the
        StreamReader.

        This function is a coroutine.

        Args:
            loop: asyncio loop
            limit: line length limit
        """
        if not limit:
            # pylint: disable-msg=protected-access
            limit = asyncio.streams._DEFAULT_LIMIT      # type: ignore

        reader = asyncio.StreamReader(limit=limit, loop=self.loop)
        protocol = asyncio.StreamReaderProtocol(reader, loop=self.loop)
        transport, _ = yield from create_serial_connection(
            loop=self.loop,
            protocol_factory=lambda: protocol,
            **kwargs)
        writer = asyncio.StreamWriter(transport, protocol, reader, self.loop)
        return reader, writer

    def schedule_once(self, callback, timeout=0):
        """Schedule an event in <timeout> seconds.

        If <timeout> is unspecified
        or 0, the callback will be called after the next frame is rendered.

        Args:
            callback: callback to call on timeout
            timeout: seconds to wait

        Returns:
            A :class:`ClockEvent` instance.
        """
        if not callable(callback):
            raise AssertionError('callback must be a callable, got %s' % callback)

        event = self.loop.call_later(delay=timeout, callback=callback)

        if self._debug_to_console or self._debug_to_file:
            self.debug_log("Scheduled a one-time clock callback (callback=%s, timeout=%s)",
                           str(callback), timeout)

        return event

    def schedule_interval(self, callback, timeout):
        """Schedule an event to be called every <timeout> seconds.

        Args:
            callback: callback to call on timeout
            timeout: period to wait

        Returns:
            A PeriodicTask object.
        """
        if not callable(callback):
            raise AssertionError('callback must be a callable, got {}'.format(callback))

        periodic_task = PeriodicTask(timeout, self.loop, callback)

        if self._debug_to_console or self._debug_to_file:
            self.debug_log("Scheduled a recurring clock callback (callback=%s, timeout=%s)",
                           str(callback), timeout)

        return periodic_task

    @staticmethod
    def unschedule(event):
        """Remove a previously scheduled event. Wrapper for cancel for compatibility to kivy clock.

        Args:
            event: Event to cancel
        """
        try:
            event.cancel()
        except Exception:     # pylint: disable-msg=broad-except
            raise AssertionError("Broken unschedule: {} {}".format(event, type(event)))
