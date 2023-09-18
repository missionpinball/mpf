"""Base class for serial communicator."""
from typing import Optional

import asyncio
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from mpf.core.utility_functions import Util


MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

HEX_FORMAT = " 0x%02x"


class BaseSerialCommunicator:

    """Basic Serial Communcator for platforms."""

    __slots__ = ["machine", "platform", "log", "debug", "port", "baud", "xonxoff", "reader", "writer", "read_task"]

    # pylint: disable=too-many-arguments
    def __init__(self, platform, port: str, baud: int, xonxoff=False) -> None:
        """initialize Serial Connection Hardware.

        Args:
        ----
            platform(mpf.core.platform.BasePlatform): the platform
            port: Port to open.
            baud: Baudrate to use
            xonxoff (bool): Use xonxoff as flow control
        """
        self.machine = platform.machine     # type: MachineController
        self.platform = platform
        self.log = self.platform.log
        self.debug = self.platform.config['debug']
        self.port = port
        self.baud = baud
        self.xonxoff = xonxoff
        self.reader = None      # type: Optional[asyncio.StreamReader]
        self.writer = None      # type: Optional[asyncio.StreamWriter]
        self.read_task = None

    async def connect(self):
        """Connect to the hardware."""
        await self._connect_to_hardware(self.port, self.baud, self.xonxoff)

    async def _connect_to_hardware(self, port, baud, xonxoff=False):
        self.log.info("Connecting to %s at %sbps", port, baud)
        while True:
            try:
                connector = self.machine.clock.open_serial_connection(
                    url=port, baudrate=baud, limit=0, xonxoff=xonxoff,
                    bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE)
                self.reader, self.writer = await connector
            except SerialException:
                if not self.machine.options["production"]:
                    raise

                # if we are in production mode retry
                await asyncio.sleep(.1)
                self.log.debug("Connection to %s failed. Will retry.", port)
            else:
                # we got a connection
                break

        serial = self.writer.transport.serial
        if hasattr(serial, "set_low_latency_mode"):
            try:
                serial.set_low_latency_mode(True)
            except (NotImplementedError, ValueError) as e:
                self.log.info("Could not set %s to low latency mode: %s", port, e)

        # defaults are slightly high for our usecase
        self.writer.transport.set_write_buffer_limits(2048, 1024)

        # read everything which is sitting in the serial
        self.writer.transport.serial.reset_input_buffer()
        # clear buffer
        # pylint: disable-msg=protected-access
        self.reader._buffer = bytearray()

        await self._identify_connection()

    async def start_read_loop(self):
        """Start the read loop."""
        self.read_task = asyncio.create_task(self._socket_reader())
        self.read_task.add_done_callback(Util.raise_exceptions)

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

    async def _identify_connection(self):
        """initialize and identify connection."""
        raise NotImplementedError("Implement!")

    def stop(self):
        """Stop and shut down this serial connection."""
        self.log.error("Stop called on serial connection %s", self.port)
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
            msg: Byes of the message you want to send.
        """
        if self.debug:
            self.log.debug("%s sending: %s (%s)", self, msg, "".join(HEX_FORMAT % b for b in msg))
        self.writer.write(msg)

    def _parse_msg(self, msg):
        """Parse a message.

        Msg may be partial.

        Args:
        ----
            msg: Bytes of the message (part) received.
        """
        raise NotImplementedError("Implement!")

    def __repr__(self):
        """Return str representation."""
        return self.port

    async def _socket_reader(self):
        while True:
            resp = await self.read(128)
            if resp is None:
                return
            self._parse_msg(resp)
