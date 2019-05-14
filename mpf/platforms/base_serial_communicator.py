"""Base class for serial communicator."""
import asyncio

from serial import SerialException

MYPY = False
if MYPY:   # pragma: no cover
    from typing import Generator


class BaseSerialCommunicator:

    """Basic Serial Communcator for platforms."""

    __slots__ = ["machine", "platform", "log", "debug", "port", "baud", "xonxoff", "reader", "writer", "read_task"]

    # pylint: disable=too-many-arguments
    def __init__(self, platform, port: str, baud: int, xonxoff=False) -> None:
        """Initialise Serial Connection Hardware.

        Args:
            platform(mpf.core.platform.BasePlatform): the platform
            port:
            baud:
        """
        self.machine = platform.machine
        self.platform = platform
        self.log = self.platform.log
        self.debug = self.platform.config['debug']
        self.port = port
        self.baud = baud
        self.xonxoff = xonxoff
        self.reader = None      # type: asyncio.StreamReader
        self.writer = None      # type: asyncio.StreamWriter
        self.read_task = None   # type: Generator[int, None, None]

    @asyncio.coroutine
    def connect(self):
        """Connect to the hardware."""
        yield from self._connect_to_hardware(self.port, self.baud, self.xonxoff)

    @asyncio.coroutine
    def _connect_to_hardware(self, port, baud, xonxoff=False):
        self.log.info("Connecting to %s at %sbps", port, baud)
        while True:
            try:
                connector = self.machine.clock.open_serial_connection(
                    url=port, baudrate=baud, limit=0, xonxoff=xonxoff)
                self.reader, self.writer = yield from connector
            except SerialException:
                if not self.machine.options["production"]:
                    raise
                else:
                    # if we are in production mode retry
                    yield from asyncio.sleep(.1, loop=self.machine.clock.loop)
                    self.log.debug("Connection to %s failed. Will retry.", port)
            else:
                # we got a connection
                break

        # defaults are slightly high for our usecase
        self.writer.transport.set_write_buffer_limits(2048, 1024)

        # read everything which is sitting in the serial
        self.writer.transport.serial.reset_input_buffer()
        # clear buffer
        # pylint: disable-msg=protected-access
        self.reader._buffer = bytearray()

        yield from self._identify_connection()

    @asyncio.coroutine
    def start_read_loop(self):
        """Start the read loop."""
        self.read_task = self.machine.clock.loop.create_task(self._socket_reader())
        self.read_task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    @asyncio.coroutine
    # pylint: disable-msg=inconsistent-return-statements
    def readuntil(self, separator, min_chars: int = 0):
        """Read until separator.

        Args:
            separator: Read until this separator byte.
            min_chars: Minimum message length before separator
        """
        # asyncio StreamReader only supports this from python 3.5.2 on
        buffer = b''
        while True:
            char = yield from self.reader.readexactly(1)
            buffer += char
            if char == separator and len(buffer) > min_chars:
                return buffer

    @asyncio.coroutine
    def _identify_connection(self):
        """Initialise and identify connection."""
        raise NotImplementedError("Implement!")

    def stop(self):
        """Stop and shut down this serial connection."""
        self.log.error("Stop called on serial connection %s", self.port)
        if self.read_task:
            self.read_task.cancel()
            self.read_task = None
        if self.writer:
            self.writer.close()
            self.writer = None

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
            msg: Byes of the message you want to send.
        """
        if self.debug:
            self.log.debug("Sending: %s (%s)", msg, "".join(" 0x%02x" % b for b in msg))
        self.writer.write(msg)

    def _parse_msg(self, msg):
        """Parse a message.

        Msg may be partial.
        Args:
            msg: Bytes of the message (part) received.
        """
        raise NotImplementedError("Implement!")

    def __repr__(self):
        """Return str representation."""
        return self.port

    @asyncio.coroutine
    def _socket_reader(self):
        while True:
            try:
                resp = yield from self.reader.read(100)
            except asyncio.CancelledError:  # pylint: disable-msg=try-except-raise
                raise
            except Exception as e:  # pylint: disable-msg=broad-except
                self.log.warning("Serial error: {}".format(e))
                resp = None

            # we either got empty response (-> socket closed) or and error
            if not resp:
                self.log.warning("Serial closed.")
                self.machine.stop("Serial {} closed.".format(self.port))
                return

            if self.debug:
                self.log.debug("%s received: %s (%s)", self, resp, "".join(" 0x%02x" % b for b in resp))
            self._parse_msg(resp)
