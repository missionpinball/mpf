# mpf.tests.test_Fast_Communicator
"""Unit tests for FastSerialCommunicator's response and inbound-parse paths.

Two related FAST startup failures are covered here:

* Response timeout/retry (#2036): a single lost serial response used to freeze
  MPF init forever, because the asyncio timeout was wrapped around
  send_and_wait_for_response() (which only queues the message and returns
  immediately) while the real wait on done_waiting had no timeout.
* Inbound resync: after an unclean shutdown the board can clock out leftover,
  un-terminated bytes that fuse onto the front of the next real message
  (``<junk>ID:exp ...``). The parser must recover the real message instead of
  dropping it or crashing on the un-decodable prefix, and connect() must drain
  that leftover burst before the handshake.

These drive the relevant methods directly with a stubbed I/O surface so the
paths are exercised deterministically without a real serial port.
"""
import asyncio
import unittest
from unittest.mock import MagicMock

from mpf.platforms.fast.communicators.base import FastSerialCommunicator


def _make_comm():
    """Build a FastSerialCommunicator with just the attributes the
    send/response and parse paths touch, bypassing __init__ (which needs a
    platform, serial port and logging setup)."""
    comm = object.__new__(FastSerialCommunicator)
    comm.send_queue = asyncio.Queue()
    comm.pause_sending_until = ''
    comm.pause_sending_flag = asyncio.Event()
    comm.no_response_waiting = asyncio.Event()
    comm.done_waiting = asyncio.Event()
    comm.no_response_waiting.set()  # not waiting for anything initially
    comm.config = {'port': 'com-test'}
    comm.log = MagicMock()
    # parse-path attributes
    comm.received_msg = b''
    comm.ignore_decode_errors = False
    comm.port_debug = False
    comm.message_processors = {}
    comm.machine = MagicMock()
    comm.machine.is_shutting_down = False
    return comm


class _FakeReader:
    """Minimal asyncio-style reader: yields queued chunks, then blocks so a
    wait_for() against it times out the way a quiet serial port would."""

    def __init__(self, chunks):
        self.chunks = list(chunks)

    async def read(self, n):
        del n
        if self.chunks:
            return self.chunks.pop(0)
        await asyncio.sleep(10)  # never completes within the test's quiet_period
        return b''


class TestFastCommunicatorRetry(unittest.TestCase):

    def test_returns_when_response_processed(self):
        """Happy path: the board answers, so the call returns after exactly one
        send and leaves no retry behind."""
        async def scenario():
            comm = _make_comm()

            async def responder():
                # Wait for the message to be queued, then mimic the reader
                # dispatching the processed response.
                await comm.send_queue.get()
                comm.no_response_waiting.set()
                comm.done_processing_msg_response()

            responder_task = asyncio.ensure_future(responder())
            await asyncio.wait_for(
                comm.send_and_wait_for_response_processed(
                    'ID@48:', 'ID:', timeout=1, max_retries=3),
                timeout=5)
            await responder_task
            return comm

        comm = asyncio.run(scenario())
        # exactly one message was sent (no spurious retries)
        self.assertEqual(comm.send_queue.qsize(), 0)

    def test_raises_instead_of_hanging_when_no_response(self):
        """The bug: a lost response hung forever. Now it must retry the
        configured number of times and then raise, never hang."""
        async def scenario():
            comm = _make_comm()
            sent = []

            # Drain whatever gets queued so the writer-side gate doesn't matter,
            # and count the sends to prove resends actually fire.
            async def drain():
                while True:
                    item = await comm.send_queue.get()
                    sent.append(item)

            drain_task = asyncio.ensure_future(drain())
            with self.assertRaises(AssertionError) as ctx:
                # Bound the whole thing: if the fix regressed and this hangs,
                # wait_for turns it into a test failure rather than a frozen run.
                await asyncio.wait_for(
                    comm.send_and_wait_for_response_processed(
                        'ID@48:', 'ID:', timeout=0.01, max_retries=3),
                    timeout=5)
            drain_task.cancel()
            return ctx.exception, sent

        exc, sent = asyncio.run(scenario())
        # error message should name the port and the message for debuggability
        self.assertIn('com-test', str(exc))
        self.assertIn('ID@48:', str(exc))
        # 1 initial attempt + 3 retries = 4 sends; proves the retry path is live
        # (previously it was unreachable and the call just blocked).
        self.assertEqual(len(sent), 4)

    def test_unlimited_retries_eventually_succeed(self):
        """max_retries=-1 (used by ID polls) must keep retrying and succeed once
        the board finally answers, rather than spinning on a dead gate."""
        async def scenario():
            comm = _make_comm()

            async def flaky_responder():
                # Ignore the first two sends (lost responses), answer the third.
                await comm.send_queue.get()
                await comm.send_queue.get()
                await comm.send_queue.get()
                comm.no_response_waiting.set()
                comm.done_processing_msg_response()

            responder_task = asyncio.ensure_future(flaky_responder())
            await asyncio.wait_for(
                comm.send_and_wait_for_response_processed(
                    'ID@48:', 'ID:', timeout=0.01, max_retries=-1),
                timeout=5)
            await responder_task

        # Must complete without raising.
        asyncio.run(scenario())


class TestFastCommunicatorResync(unittest.TestCase):

    def test_resync_segment_recovers_message_after_junk(self):
        """A real message fused onto the tail of un-decodable junk is recovered
        from the earliest known header."""
        comm = _make_comm()
        comm.message_processors = {'ID:': None, 'XX:': None}
        self.assertEqual(
            comm._resync_segment(b'\x81\xb5\xc1ID:exp fp-exp-0081 0.48'),
            'ID:exp fp-exp-0081 0.48')

    def test_resync_segment_returns_none_without_known_header(self):
        """Pure junk with no recognizable header can't be recovered."""
        comm = _make_comm()
        comm.message_processors = {'ID:': None}
        self.assertIsNone(comm._resync_segment(b'\x81\xb5\xc1\x00\xff'))

    def test_parse_recovers_id_response_fused_to_junk(self):
        """The franken-string case: leftover bytes with no <CR> fuse onto the
        ID: reply. The processor must still fire with the real payload."""
        comm = _make_comm()
        received = []
        comm.message_processors = {'ID:': received.append}
        comm.parse_incoming_raw_bytes(b'\x81\xb5\xc1ID:exp fp-exp-0081 0.48\r')
        self.assertEqual(received, ['exp fp-exp-0081 0.48'])

    def test_parse_raises_on_unrecoverable_junk(self):
        """Un-decodable data with no known header still raises during init
        (ignore_decode_errors False), preserving the original safety net."""
        comm = _make_comm()
        comm.ignore_decode_errors = False
        comm.message_processors = {'ID:': lambda m: None}
        with self.assertRaises(UnicodeDecodeError):
            comm.parse_incoming_raw_bytes(b'\x81\xb5\xc1\r')

    def test_parse_drops_unrecoverable_junk_when_ignoring(self):
        """With ignore_decode_errors set (e.g. during connect), unrecoverable
        junk is dropped rather than raised."""
        comm = _make_comm()
        comm.ignore_decode_errors = True
        comm.message_processors = {'ID:': lambda m: None}
        # must not raise
        comm.parse_incoming_raw_bytes(b'\x81\xb5\xc1\r')

    def test_drain_serial_discards_until_quiet(self):
        """_drain_serial reads and discards leftover bytes, returning once the
        stream goes quiet (the read blocks past quiet_period)."""
        async def scenario():
            comm = _make_comm()
            comm.reader = _FakeReader([b'leftover-junk', b'more-junk'])
            comm.machine.clock.loop.time.return_value = 0.0  # deadline never hit
            await asyncio.wait_for(
                comm._drain_serial(quiet_period=0.01, max_drain_time=5),
                timeout=5)
            return comm

        comm = asyncio.run(scenario())
        # everything was consumed before the quiet timeout returned
        self.assertEqual(comm.reader.chunks, [])
