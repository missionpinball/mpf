import asyncio
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util

HEX_FORMAT = " 0x%02x"

MIN_FW = version.parse('0.00') # override in subclass

class FastSerialCommunicator:

    """Handles the serial communication to the FAST platform."""

    ignored_messages = []

    # __slots__ = ["aud", "dmd", "remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
    #              "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
    #              "send_queue", "is_retro", "is_nano", "machine", "platform", "log", "debug", "read_task",
    #              "reader", "writer"]

    def __init__(self, platform, processor, config):
        """Initialize FastSerialCommunicator."""
        self.platform = platform
        self.remote_processor = processor
        self.config = config
        self.writer = None
        self.reader = None
        self.read_task = None
        self.received_msg = b''
        self.log = platform.log
        self.machine = platform.machine
        self.fast_debug = platform.debug
        self.port_debug = config['debug']
        self.paused = False
        self.resume_msg = None

        self.remote_firmware = None

        if self.port_debug:
            self.send = self.debug_send
        else:
            self.send = self.optimized_send

    def __repr__(self):
        return f'<FAST {self.remote_processor.upper()} Communicator: {self.config["port"]}>'

    async def connect(self):
        """Connect to the serial port."""
        self.log.info("Connecting to %s at %sbps", self.config['port'], self.config['baud'])
        while True:
            try:
                connector = self.machine.clock.open_serial_connection(
                    url=self.config['port'], baudrate=self.config['baud'], limit=0, xonxoff=False,
                    bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE)
                self.reader, self.writer = await connector
            except SerialException:
                if not self.machine.options["production"]:
                    raise

                # if we are in production mode retry
                await asyncio.sleep(.1)
                self.log.warning("Connection to %s failed. Will retry.", self.config['port'])
            else:
                # we got a connection
                break

        serial = self.writer.transport.serial
        if hasattr(serial, "set_low_latency_mode"):
            try:
                serial.set_low_latency_mode(True)
            except (NotImplementedError, ValueError) as e:
                self.log.debug(f"Could not enable low latency mode for {self.config['port']}. {e}")

        # defaults are slightly high for our use case
        self.writer.transport.set_write_buffer_limits(2048, 1024)

        # read everything which is sitting in the serial
        self.writer.transport.serial.reset_input_buffer()
        # clear buffer
        # pylint: disable-msg=protected-access
        self.reader._buffer = bytearray()

        msg = ''

        # send enough dummy commands to clear out any buffers on the FAST
        # board that might be waiting for more commands
        self.send(' ' * 256 * 4)

        while True:
            self.platform.debug_log(f"Sending 'ID:' command to {self.config['port']}")
            self.send('ID:')
            msg = await self._read_with_timeout(.5)

            # ignore XX replies here.
            while msg.startswith('XX:'):
                msg = await self._read_with_timeout(.5)

            if msg.startswith('ID:'):
                break

            await asyncio.sleep(.5)

        try:
            self.remote_processor, self.remote_model, self.remote_firmware = msg[3:].split()
        except ValueError:
            # Some boards (e.g. FP-CPU-2000) do not include a processor type, default to NET
            self.remote_model, self.remote_firmware = msg[3:].split()
            self.remote_processor = 'NET'

            # todo move this to a subclass
            # Neuron 2.06 returns `ID:NET FP-CPU-2000  02.06`

        self.platform.log.info(f"Connected to {self.remote_processor} processor on {self.remote_model} with firmware v{self.remote_firmware}")

    async def init(self):

        self.machine.variables.set_machine_var("fast_{}_firmware".format(self.remote_processor.lower()),
                                               self.remote_firmware)
        '''machine_var: fast_(x)_firmware

        desc: Holds the version number of the firmware for the processor on
        the FAST Pinball controller that's connected. The "x" is replaced with
        processor attached (e.g. "net", "exp", etc).
        '''

        self.machine.variables.set_machine_var("fast_{}_model".format(self.remote_processor.lower()), self.remote_model)

        '''machine_var: fast_(x)_model

        desc: Holds the model number of the board for the processor on
        the FAST Pinball controller that's connected. The "x" is replaced with
        processor attached (e.g. "net", "exp", etc).
        '''

        if version.parse(self.remote_firmware) < MIN_FW:
            raise AssertionError(f'Firmware version mismatch. MPF requires the {self.remote_processor} processor '
                                 f'to be firmware {self.MIN_FW}, but yours is {self.remote_firmware}')

    async def _read_with_timeout(self, timeout):
        try:
            msg_raw = await asyncio.wait_for(self.readuntil(b'\r'), timeout=timeout)
        except asyncio.TimeoutError:
            return ""
        return msg_raw.decode()

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
                if self.port_debug:
                    self.log.debug("%s received: %s (%s)", self, buffer, "".join(HEX_FORMAT % b for b in buffer))
                return buffer

    def stop(self):
        """Stop and shut down this serial connection."""
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


    def debug_send(self, msg, resume_msg=''):
        # this is accessed via self.send and mapped to the correct send method so we don't have a bunch of if statements

        self.writer.write(msg.encode() + b'\r')

        if resume_msg:
            self.log.info(resume_msg)
            self.writer.transport.pause_writing()
            # TODO self.writer.transport.pause_reading()
            # TODO self.writer.transport._paused()
            self.resume_msg = msg
            self.paused = True

        # Don't log W(atchdog) or L(ight) messages, they are noisy
        if msg[0] != "W" and msg[0] != "L":  # todo move to net instance
            self.platform.log.info("Send: %s", msg)

    def optimized_send(self, msg):
        # this is accessed via self.send and mapped to the correct send method so we don't have a bunch of if statements

        self.writer.write(msg.encode() + b'\r')

    def send_raw(self, msg):
        # Sends a message as is, without encoding or adding a <CR> character
        self.platform.debug_log("EXP send: %s", msg)
        self.writer.write(msg)

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            # TODO add logging

            if not msg:
                continue

            msg = msg.decode()

            if self.paused and msg == self.resume_msg:
                self.writer.transport.resume_writing()
                self.paused = False
                self.resume_msg = None
                continue

            if msg not in self.ignored_messages:
                self.platform.process_received_message(msg, self.remote_processor)

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
            self.machine.stop("Serial {} closed.".format(self.config["port"]))
            return None

        if self.port_debug:
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
