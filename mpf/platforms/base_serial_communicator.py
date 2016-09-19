"""Base class for serial communicator."""
import asyncio


class BaseSerialCommunicator(object):

    """Basic Serial Communcator for platforms."""

    # pylint: disable=too-many-arguments
    def __init__(self, platform, port: str, baud: int):
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
        self.reader = None
        self.writer = None

        self.machine.clock.loop.run_until_complete(self._connect_to_hardware(port, baud))

    @asyncio.coroutine
    def _connect_to_hardware(self, port, baud):
        self.log.info("Connecting to %s at %sbps", port, baud)

        connector = self.machine.clock.open_serial_connection(
            url=port, baudrate=baud, limit=0)
        self.reader, self.writer = yield from connector

        yield from self._identify_connection()

        self.read_task = self.machine.clock.loop.create_task(self._socket_reader())
        self.read_task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    @asyncio.coroutine
    def readuntil(self, separator, min_chars: int=0):
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
        self.read_task.cancel()
        self.writer.close()

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

    @asyncio.coroutine
    def _socket_reader(self):
        while True:
            try:
                resp = yield from self.reader.read(100)
            # pylint: disable-msg=broad-except
            except Exception as e:
                self.log.warning("Serial error: {}".format(e))
                resp = None

            # we either got empty response (-> socket closed) or and error
            if not resp:
                self.log.warning("Serial closed.")
                self.machine.stop()
                return

            if self.debug:
                self.log.debug("Received: %s (%s)", resp, "".join(" 0x%02x" % b for b in resp))
            self._parse_msg(resp)
