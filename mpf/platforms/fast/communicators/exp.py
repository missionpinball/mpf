import asyncio
from packaging import version
from typing import Optional
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util

# Minimum firmware versions needed for this module
from mpf.platforms.fast.fast_io_board import FastIoBoard

EXP_MIN_FW = version.parse('0.10')

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

HEX_FORMAT = " 0x%02x"

class FastExpCommunicator:

    """Handles the serial communication to the FAST platform."""

    ignored_messages = ['RX:P',  # RGB Pass
                        'XX:U',
                        'XX:N',
                        ]

    # __slots__ = ["remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
    #              "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
    #              "send_queue", "is_retro", "is_legacy", "machine", "platform", "log", "debug", "port", "baud",
    #              "xonxoff", "reader", "writer", "read_task", "boards"]

    def __init__(self, platform, reader, writer):
        """Initialize communicator.

        Args:
        ----
            platform(mpf.platforms.fast.fast.HardwarePlatform): the fast hardware platform
            reader: asyncio.StreamReader
            writer: asyncio.StreamWriter
        """

        self.platform = platform
        self.reader = reader      # type: Optional[asyncio.StreamReader]
        self.writer = writer      # type: Optional[asyncio.StreamWriter]
        self.machine = platform.machine     # type: MachineController
        self.log = self.platform.log
        self.debug = self.platform.config['debug']

        # self.max_messages_in_flight = 10
        # self.messages_in_flight = 0
        # self.ignored_messages_in_flight = {b'-N', b'/N', b'/L', b'-L'}
        self.boards = dict()  # keys = board addresses, values = FastExpBoard objects
        self.led_ports = set()  # set of LED port objects
        # this is a set since if a port doesn't have any LEDs attached then we want it to not exist in our world

        self.active_board = None  # type: Optional[FastExpBoard]
        self.exp_boards = dict()  # str address: FastExpBoard

        self.send_ready = asyncio.Event()
        self.send_ready.set()
        self.write_task = None
        self.read_task = None

        self.received_msg = b''

        self.send_queue = asyncio.Queue()

    async def init(self):

        # TODO Firmware checking
        # Existing fw checks assume only one board per connection, but we need to check each board, so this is a future TODO

        # Register the connection so when we query the boards we know what responses to expect
        self.platform.register_processor_connection('EXP', self)

        self.write_task = self.machine.clock.loop.create_task(self._socket_writer())
        self.write_task.add_done_callback(Util.raise_exceptions)

        return self

    # Duplicated from FastSerialConnector for now
    # pylint: disable-msg=inconsistent-return-statements
    async def readuntil(self, separator, min_chars: int = 0):
        """Read until separator.

        Args:
        ----
            separator: Read until this separator byte.
            min_chars: Minimum message length before separator
        """
        assert self.reader is not None
        # asyncio StreamReader only supports this from python 3.5.2 on
        buffer = b''
        while True:
            char = await self.reader.readexactly(1)
            buffer += char
            if char == separator and len(buffer) > min_chars:
                if self.debug:
                    self.log.debug("%s received: %s (%s)", self, buffer, "".join(HEX_FORMAT % b for b in buffer))
                return buffer

    def stop(self):
        """Stop and shut down this serial connection."""
        if self.write_task:
            self.write_task.cancel()
            self.write_task = None
        self.log.error("Stop called on serial connection %s", self.remote_processor)
        if self.read_task:
            self.read_task.cancel()
            self.read_task = None
        if self.writer:
            self.writer.close()
            if hasattr(self.writer, "wait_closed"):
                # Python 3.7+ only
                self.machine.clock.loop.run_until_complete(self.writer.wait_closed())
            self.writer = None

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
        ----
            msg: String of the message you want to send. THe <CR> character will
                be added automatically.

        """
        self.send_queue.put_nowait(msg)

    def _send(self, msg):

        # TODO for now EXP bus will not track any messages. If there are ones we want
        # to track in the future (maybe?), we can add here

        self.writer.write(msg.encode() + b'\r')
        self.platform.log.debug("Sending without message flight tracking: %s", msg)

    async def _socket_writer(self):
        while True:
            msg = await self.send_queue.get()
            try:
                await asyncio.wait_for(self.send_ready.wait(), 1.0)
            except asyncio.TimeoutError:
                self.log.warning("Port %s was blocked for more than 1s. Resetting send queue! If this happens "
                                 "frequently report a bug!", self.port)
                self.send_ready.set()

            self._send(msg)

    def __repr__(self):
        """Return str representation."""
        return f"FAST Communicator attached to EXP Bus"

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            if msg[:2] not in self.ignored_messages_in_flight:

                self.messages_in_flight -= 1
                if self.messages_in_flight <= self.max_messages_in_flight or not self.read_task:
                    self.send_ready.set()
                if self.messages_in_flight < 0:
                    self.log.warning("Port %s received more messages than "
                                     "were sent! Resetting!",
                                     self.remote_processor)
                    self.messages_in_flight = 0

            if not msg:
                continue

            if msg.decode() not in self.ignored_messages:
                self.platform.process_received_message(msg.decode(), self.remote_processor)

    async def read(self, n=-1):
        """Read up to `n` bytes from the stream and log the result if debug is true.

        See :func:`StreamReader.read` for details about read and the `n` parameter.
        """
        try:
            resp = await self.reader.read(n)
        except asyncio.CancelledError:  # pylint: disable-msg=try-except-raise
            raise
        except Exception as e:  # pylint: disable-msg=broad-except
            self.log.warning("Serial error: {}".format(e))
            return None

        # we either got empty response (-> socket closed) or and error
        if not resp:
            self.log.warning("Serial closed.")
            self.machine.stop("Serial {} closed.".format(self.port))
            return None

        if self.debug:
            self.log.debug("%s received: %s (%s)", self, resp, "".join(HEX_FORMAT % b for b in resp))
        return resp

    async def start_read_loop(self):
        """Start the read loop."""
        self.read_task = self.machine.clock.loop.create_task(self._socket_reader())
        self.read_task.add_done_callback(Util.raise_exceptions)

    async def _socket_reader(self):
        while True:
            resp = await self.read(128)
            if resp is None:
                return
            self._parse_msg(resp)

    def set_active_board(self, board):

        self.send(f"EA:{board.address}")
        self.active_board = board