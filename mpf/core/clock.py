"""MPF clock and main loop."""
import logging
import asyncio
from functools import partial

from mpf.pyserial_asyncio.serial_asyncio import create_serial_connection


class PeriodicTask:

    """A periodic asyncio task."""

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
        # TODO: remove dt parameter from all callbacks
        self._callback(None)
        self._schedule()

    def cancel(self):
        """Cancel periodic task."""
        self._canceled = True


class ClockBase:

    """A clock object with event support."""

    def __init__(self):
        """Initialise clock."""
        self._log = logging.getLogger("Clock")
        self._log.debug("Starting tickless clock")
        self.loop = self._create_event_loop()

    # pylint: disable-msg=no-self-use
    def _create_event_loop(self):
        return asyncio.get_event_loop()

    def run(self):
        """Run the clock."""
        self.loop.run_forever()

    def get_time(self):
        """Get the last tick made by the clock."""
        return self.loop.time()

    @asyncio.coroutine
    def start_server(self, client_connected_cb, host=None, port=None, **kwd):
        """Start a server."""
        yield from asyncio.streams.start_server(client_connected_cb, host, port, **kwd)

    def open_connection(self, host=None, port=None, *,
                        limit=None, **kwds):
        """A wrapper for create_connection() returning a (reader, writer) pair.

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
    def open_serial_connection(self, limit=None, **kwargs):
        """A wrapper for create_serial_connection() returning a (reader, writer) pair.

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
            limit = asyncio.streams._DEFAULT_LIMIT

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

        # TODO: remove dt parameter from all callbacks
        new_callback = partial(callback, None)
        event = self.loop.call_later(delay=timeout, callback=new_callback)

        self._log.debug("Scheduled a one-time clock callback (callback=%s, timeout=%s)",
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

        self._log.debug("Scheduled a recurring clock callback (callback=%s, timeout=%s)",
                        str(callback), timeout)

        return periodic_task

    @staticmethod
    def unschedule(event):
        """Remove a previously scheduled event. Wrapper for cancel for compatibility to kivy clock.

        Args:
            event: Event to cancel
        """
        if isinstance(event, (asyncio.Handle, PeriodicTask)):
            event.cancel()
        else:
            raise AssertionError("Broken unschedule")
