"""MPF clock and main loop."""
import logging
import asyncio


class PeriodicTask:

    """A periodic asyncio task."""

    def __init__(self, interval, loop, callback):
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
        self._callback(None)
        self._schedule()

    def cancel(self):
        """Cancel periodic task."""
        self._canceled = True


class ClockBase:
    """A clock object with event support."""

    def __init__(self, machine):
        """Initialise clock."""
        self._log = logging.getLogger("Clock")
        self._log.debug("Starting tickless clock")
        self.loop = machine.get_event_loop()

    def run(self):
        """Run the clock."""
        self.loop.run_forever()

    def get_time(self):
        """Get the last tick made by the clock."""
        return self.loop.time()

    def schedule_socket_read_callback(self, socket, callback):
        """Schedule a callback when the socket is ready.

        Args:
            socket: Any type of socket which can be passed to select.
            callback: Callback to call
        """
        self.loop.add_reader(fd=socket, callback=callback)

    def unschedule_socket_read_callback(self, socket):
        """Remove a socket callback which has to be registered.

        Args:
            socket: Socket so remove.
        """
        self.loop.remove_reader(fd=socket)

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

        new_callback = lambda: callback(None)
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
            raise AssertionError('callback must be a callable, got %s' % callback)

        periodic_task = PeriodicTask(timeout, self.loop, callback)

        self._log.debug("Scheduled a recurring clock callback (callback=%s, timeout=%s, priority=%s)",
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
