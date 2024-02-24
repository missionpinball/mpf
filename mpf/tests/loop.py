import datetime
import selectors
import socket
from asyncio import base_events, events      # type: ignore
import collections
import heapq

# A class to manage set of next events:
from asyncio.selector_events import _SelectorSocketTransport    # type: ignore # noqa

import asyncio

import time

from mpf.core.clock import ClockBase
from serial_asyncio import SerialTransport


class NextTimers:

    """Next timers."""

    __slots__ = ["_timers_set", "_timers_heap"]

    def __init__(self):
        # Timers set. Used to check uniqueness:
        self._timers_set = set()
        # Timers heap. Used to get the closest timer event:
        self._timers_heap = []

    def add(self, when):
        """
        Add a timer (Future event).
        """
        # We don't add a time twice:
        if when in self._timers_set:
            return

        # Add to set:
        self._timers_set.add(when)
        # Add to heap:
        heapq.heappush(self._timers_heap, when)

    def is_empty(self):
        return not self._timers_set

    def pop_closest(self):
        """
        Get closest event timer. (The one that will happen the soonest).
        """
        try:
            when = heapq.heappop(self._timers_heap)
            self._timers_set.remove(when)
        except IndexError:
            raise IndexError('NextTimers is empty')

        return when

    def __repr__(self):
        return str(self._timers_set)


class _TestTransport:

    __slots__ = ["_loop", "_sock"]

    def __init__(self, loop, sock):
        self._loop = loop
        self._sock = sock
        self._loop.add_reader(self._sock, self._read_ready)

    def _read_ready(self):
        pass

    def write(self, msg):
        pass

    def disconnect(self):
        pass


class MockFd:

    __slots__ = ["is_open"]

    def __init__(self):
        self.is_open = False

    def open(self):
        if self.is_open:
            raise AssertionError("Serial already open")
        self.is_open = True

    def read_ready(self):
        if not self.is_open:
            raise AssertionError("Serial not open")
        return False

    def send(self, data):
        if not self.is_open:
            raise AssertionError("Serial not open")
        return len(data)

    def fileno(self):
        return self

    def write_ready(self):
        if not self.is_open:
            raise AssertionError("Serial not open")
        return False

    def close(self):
        self.is_open = False
        return


class MockSocket(MockFd):

    __slots__ = ["family", "type", "proto", "__dict__"]

    def __init__(self):
        super().__init__()
        self.family = socket.AF_INET
        self.type = socket.SOCK_STREAM
        self.proto = socket.IPPROTO_TCP

    def setsockopt(self, *args, **kwargs):
        pass

    def getsockname(self):
        return ""

    def getpeername(self):
        return ""

    def recv(self, size):
        raise AssertionError("Not implemented")


class MockQueueSocket(MockSocket):

    __slots__ = ["send_queue", "recv_queue"]

    def __init__(self, loop):
        super().__init__()
        self.send_queue = asyncio.Queue()
        self.recv_queue = []

    def write_ready(self):
        return True

    def read_ready(self):
        return bool(len(self.recv_queue))

    def recv(self, size):
        return self.recv_queue.pop(0)

    def send(self, data):
        self.send_queue.put_nowait(data)
        return len(data)


class MockServer:

    __slots__ = ["loop", "is_bound", "client_connected_cb"]

    def __init__(self, loop):
        self.loop = loop
        self.is_bound = asyncio.Future()
        self.client_connected_cb = None

    async def bind(self, client_connected_cb):
        self.client_connected_cb = client_connected_cb
        self.is_bound.set_result(True)

    async def add_client(self, socket):
        if not self.is_bound.done():
            raise AssertionError("Server not running")

        limit = asyncio.streams._DEFAULT_LIMIT
        reader = asyncio.streams.StreamReader(limit=limit, loop=self.loop)
        protocol = asyncio.streams.StreamReaderProtocol(reader, loop=self.loop)
        transport = _SelectorSocketTransport(self.loop, socket, protocol)
        writer = asyncio.streams.StreamWriter(transport, protocol, reader, self.loop)
        await self.client_connected_cb(reader, writer)

    def close(self):
        pass

    async def wait_closed(self):
        return True


class MockSerial(MockFd):


    def __init__(self):
        super().__init__()
        self.fd = self
        self.timeout = None

    def reset_input_buffer(self):
        pass

    def nonblocking(self):
        pass

    def flush(self):
        pass

    @property
    def out_waiting(self):
        return 0 if self.write_ready() else 1024

    def in_waiting(self):
        return 1024 if self.read_ready() else 0

    def read(self, length):
        raise AssertionError("Not implemented")


class TestSelector(selectors.BaseSelector):

    __slots__ = ["keys"]

    def __init__(self):
        self.keys = {}

    def register(self, fileobj, events, data=None):
        key = selectors.SelectorKey(fileobj, 0, events, data)
        self.keys[fileobj] = key
        return key

    def unregister(self, fileobj):
        return self.keys.pop(fileobj)

    def select(self, timeout=None):
        del timeout
        if not self.keys:
            return []
        ready = []
        for sock, key in self.keys.items():
            if sock.read_ready():
                ready.append((key, selectors.EVENT_READ))
            if sock.write_ready():
                ready.append((key, selectors.EVENT_WRITE))
        return ready

    def get_map(self):
        return self.keys


# Based on TestLoop from asyncio.test_utils:
class TimeTravelLoop(base_events.BaseEventLoop):

    """
    Loop for unittests. Passes time without waiting, but makes sure events
    happen in the correct order.
    """

    __slots__ = ["readers", "writers", "_time", "_clock_resolution", "_timers", "_selector", "_transports",
                 "_wait_for_external_executor", "_stopped"]

    def __init__(self):
        self.readers = {}
        self.writers = {}

        super().__init__()

        self._time = 0
        self._stopped = False
        self._clock_resolution = 1e-9
        self._timers = NextTimers()
        self._selector = TestSelector()
        self._transports = {}   # needed for newer asyncio on windows
        self.reset_counters()
        self._wait_for_external_executor = False

    def close(self, ignore_running_tasks=False) -> None:
        tasks = asyncio.all_tasks(loop=self)


        if not ignore_running_tasks:
            # open_tasks = [t for t in tasks if (not t.done() and not isinstance(t.get_coro(), asyncio.Lock))]
            # if open_tasks:
            #     super().close()
            #     raise AssertionError("There are still open tasks: {}".format(open_tasks))

            for task in tasks:
                task.cancel()
                try:
                    self.run_until_complete(task)
                except asyncio.CancelledError:
                    pass

        super().close()

    def time(self):
        return self._time

    # def create_task(self, coro, *, name=None):
    #     import sys
    #     import traceback
    #     traceback.print_stack(file=sys.stdout)
    #     task = super().create_task(coro, name=name)
    #     print(task.get_name())
    #     return task

    def set_time(self, time):
        """Set time in loop."""
        self._time = time

    def advance_time(self, advance):
        """Move test time forward."""
        if advance:
            self._time += advance

    def _add_reader(self, *args, **kwargs):
        return self.add_reader(*args, **kwargs)

    def add_reader(self, fd, callback, *args):
        """Add a reader callback."""
        self._check_closed()
        handle = events.Handle(callback, args, self)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            self._selector.register(fd, selectors.EVENT_READ,
                                    (handle, None))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_READ,
                                  (handle, writer))
            if reader is not None:
                reader.cancel()

    def stop(self):
        """Stop loop."""
        self._stopped = True
        super().stop()

    def _remove_reader(self, fd):
        return self.remove_reader(fd)

    def remove_reader(self, fd):
        """Remove a reader callback."""
        if self.is_closed():
            return False
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            return False
        else:
            mask, (reader, writer) = key.events, key.data
            mask &= ~selectors.EVENT_READ
            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, (None, writer))

            if reader is not None:
                reader.cancel()
                return True
            else:
                return False

    def _add_writer(self, *args, **kwargs):
        return self.add_writer(*args, **kwargs)

    def add_writer(self, fd, callback, *args):
        """Add a writer callback.."""
        self._check_closed()
        handle = events.Handle(callback, args, self)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            self._selector.register(fd, selectors.EVENT_WRITE,
                                    (None, handle))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_WRITE,
                                  (reader, handle))
            if writer is not None:
                writer.cancel()

    def _remove_writer(self, fd):
        return self.remove_writer(fd)

    def remove_writer(self, fd):
        """Remove a writer callback."""
        if self.is_closed():
            return False
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            return False
        else:
            mask, (reader, writer) = key.events, key.data
            # Remove both writer and connector.
            mask &= ~selectors.EVENT_WRITE
            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, (reader, None))

            if writer is not None:
                writer.cancel()
                return True
            else:
                return False

    def assert_writer(self, fd, callback, *args):
        assert fd in self.writers, 'fd {} is not registered'.format(fd)
        handle = self.writers[fd]
        assert handle[0] == callback, '{!r} != {!r}'.format(
            handle[0], callback)
        assert handle[1] == args, '{!r} != {!r}'.format(
            handle[1], args)

    def reset_counters(self):
        self.remove_reader_count = collections.defaultdict(int)
        self.remove_writer_count = collections.defaultdict(int)

    def run_once(self):
        if hasattr(events, "_set_running_loop"):
            events._set_running_loop(self)

        self._run_once()

        if hasattr(events, "_set_running_loop"):
            events._set_running_loop(None)

    def _run_once(self):
        # Advance time only when we finished everything at the present:
        if len(self._ready) == 0:
            if not self._timers.is_empty():
                self._time = self._timers.pop_closest()
            elif not self._closed and not self._stopped and not self._selector.select(0) and \
                    not self._wait_for_external_executor:
                raise AssertionError("Ran into an infinite loop. No socket ready and nothing scheduled.")
            if self._wait_for_external_executor:
                time.sleep(.0001)

        super()._run_once()
        if self._wait_for_external_executor:
            self._waiting_since = None

    def call_at(self, when, callback, *args, **kwargs):
        self._timers.add(when)
        return super().call_at(when, callback, *args, **kwargs)

    def _process_events(self, event_list):
        for key, mask in event_list:
            fileobj, (reader, writer) = key.fileobj, key.data
            if mask & selectors.EVENT_READ and reader is not None:
                if reader._cancelled:
                    self.remove_reader(fileobj)
                else:
                    self._add_callback(reader)
            if mask & selectors.EVENT_WRITE and writer is not None:
                if writer._cancelled:
                    self.remove_writer(fileobj)
                else:
                    self._add_callback(writer)

    def _write_to_self(self):
        pass


class TestClock(ClockBase):

    __slots__ = ["_test_loop", "_mock_sockets", "_mock_servers", "_mock_serials"]

    def __init__(self, loop):
        self._test_loop = loop
        super().__init__()
        self._mock_sockets = {}
        self._mock_servers = {}
        self._mock_serials = {}

    def get_datetime(self):
        """Create datetime based on time travel loop."""
        # for some weird reason windows does not like timestamps below 86400 so add a little bit to it
        return datetime.datetime.fromtimestamp(self.get_time() + 100000)

    def _create_event_loop(self):
        return self._test_loop

    def mock_socket(self, host, port, socket):
        """Mock a socket and use it for connections."""
        self._mock_sockets[host + ":" + str(port)] = socket

    def mock_server(self, host, port, server):
        """Mock a server and use it for connections."""
        self._mock_servers[host + ":" + str(port)] = server

    def _open_mock_socket(self, host, port):
        key = host + ":" + str(port)
        if key not in self._mock_sockets:
            raise AssertionError("socket not mocked for key {}".format(key))
        socket = self._mock_sockets[key]
        if socket.is_open:
            raise AssertionError("socket already open for key {}".format(key))

        socket.is_open = True
        return socket

    async def start_server(self, client_connected_cb, host=None, port=None, **kwd):
        """Mock listening server."""
        key = host + ":" + str(port)
        if key not in self._mock_servers:
            raise AssertionError("server not mocked for key {}".format(key))
        server = self._mock_servers[key]
        if server.is_bound.done():
            raise AssertionError("server already bound for key {}".format(key))

        await server.bind(client_connected_cb)
        return server


    async def open_connection(self, host=None, port=None, *,
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
            limit = asyncio.streams._DEFAULT_LIMIT  # type: ignore
        reader = asyncio.streams.StreamReader(limit=limit, loop=self.loop)
        protocol = asyncio.streams.StreamReaderProtocol(reader, loop=self.loop)
        sock = self._open_mock_socket(host, port)
        transport = _SelectorSocketTransport(self.loop, sock, protocol)
        writer = asyncio.streams.StreamWriter(transport, protocol, reader, self.loop)
        return reader, writer   # type: ignore

    def mock_serial(self, url, serial):
        """Mock a socket and use it for connections."""
        self._mock_serials[url] = serial

    def _open_mock_serial(self, url, do_not_open):
        key = url
        if key not in self._mock_serials:
            raise AssertionError("serial not mocked for key {}".format(key))
        serial = self._mock_serials[key]
        if not do_not_open:
            if serial.is_open:
                raise AssertionError("serial already open for key {}".format(key))

            serial.is_open = True
        return serial

    async def open_serial_connection(self, limit=None, **kwargs):     # type: ignore
        """A wrapper for create_serial_connection() returning a (reader, writer) pair.

        The reader returned is a StreamReader instance; the writer is a
        StreamWriter instance.

        The arguments are all the usual arguments to Serial(). Additional
        optional keyword arguments are loop (to set the event loop instance
        to use) and limit (to set the buffer limit passed to the
        StreamReader.

        This function is a coroutine.
        """
        if not limit:
            limit = asyncio.streams._DEFAULT_LIMIT  # type: ignore

        reader = asyncio.StreamReader(limit=limit, loop=self.loop)
        protocol = asyncio.StreamReaderProtocol(reader, loop=self.loop)
        transport = SerialTransport(self.loop, protocol, self._open_mock_serial(kwargs['url'],
                                                                                kwargs.get("do_not_open", False)))
        writer = asyncio.StreamWriter(transport, protocol, reader, self.loop)
        return reader, writer
