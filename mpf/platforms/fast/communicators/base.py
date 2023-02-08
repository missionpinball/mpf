import asyncio
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from mpf.core.utility_functions import Util

HEX_FORMAT = " 0x%02x"
MIN_FW = version.parse('0.00') # override in subclass
HAS_UPDATE_TASK = False

class FastSerialCommunicator:

    """Handles the serial communication to the FAST platform."""

    ignored_messages = ['WD:P']

    # __slots__ = ["aud", "dmd", "remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
    #              "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
    #              "send_queue", "is_retro", "is_nano", "machine", "platform", "log", "debug", "read_task",
    #              "reader", "writer"]

    def __init__(self, platform, processor, config):
        """Initialize FastSerialCommunicator."""
        self.platform = platform
        self.remote_processor = processor.upper()
        self.config = config
        self.writer = None
        self.reader = None
        self.read_task = None
        self.received_msg = b''
        self.log = platform.log  # TODO child logger per processor? Different debug logger?
        self.machine = platform.machine
        self.fast_debug = platform.debug
        self.port_debug = config['debug']

        self.remote_firmware = None  # TODO some connections have more than one processor, should there be a processor object?

        self.send_ready = asyncio.Event()
        self.send_ready.set()
        self.send_queue = asyncio.Queue()
        self.no_waiting = asyncio.Event()
        self.no_waiting.set()
        self.confirm_msg = None
        self.write_task = None

        self.ignore_decode_errors = True  # TODO set to False once the connection is established
        # TODO make this a config option? meh.
        # TODO this is not implemented yet

        self.message_processors = {'XX': self._process_xx,
                                   'ID': self._process_id}
        self.current_message_processor = None

    def __repr__(self):
        return f'<FAST {self.remote_processor} Communicator>'

    async def connect(self):
        """Does several things to connect to the FAST processor.

        * Opens the serial connection
        * Clears out any data in the serial buffer
        * Starts the read & write tasks
        * Set the flag to ignore decode errors
        """
        self.log.debug(f"Connecting to {self.config['port']} at {self.config['baud']}bps")

        while True:
            try:
                connector = self.machine.clock.open_serial_connection(
                    url=self.config['port'], baudrate=self.config['baud'], limit=0, xonxoff=False,
                    bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE)
                self.reader, self.writer = await connector
            except SerialException:
                if not self.machine.options["production"]:
                    raise

                # if we are in production mode, retry
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

        self.ignore_decode_errors = True

        await self.clear_board_serial_buffer()

        self.ignore_decode_errors = False

        self.write_task = self.machine.clock.loop.create_task(self._socket_writer())
        self.write_task.add_done_callback(Util.raise_exceptions)

        self.read_task = self.machine.clock.loop.create_task(self._socket_reader())
        self.read_task.add_done_callback(Util.raise_exceptions)

    async def clear_board_serial_buffer(self):
        """Clear out the serial buffer."""

        self.write_to_port(b'\r\r\r\r')
        await asyncio.sleep(.5)

    async def init(self):

        await self.send_query('ID:')

    def _process_xx(self, msg):
        """Process the XX response."""
        self.log.warning("Received XX response: %s", msg)  # what are we going to do here? TODO

        return msg, False

    def _process_id(self, msg):
        """Process the ID response."""
        self.remote_processor, self.remote_model, self.remote_firmware = msg[3:].split()

        self.platform.log.info(f"Connected to {self.remote_processor} processor on {self.remote_model} with firmware v{self.remote_firmware}")

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
                                 f'to be firmware {MIN_FW}, but yours is {self.remote_firmware}')

        return msg, False

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
                    self.log.info(f"{self.remote_processor} <<<< {buffer}")
                return buffer

    def stop(self):
        """Stop and shut down this serial connection."""
        self.log.error("Stop called on serial connection %s", self.remote_processor)
        if self.read_task:
            self.read_task.cancel()
            self.read_task = None

        if self.write_task:
            self.write_task.cancel()
            self.write_task = None

        if self.writer:
            self.writer.close()
            if hasattr(self.writer, "wait_closed"):
                # Python 3.7+ only
                self.machine.clock.loop.run_until_complete(self.writer.wait_closed())
            self.writer = None

    async def send_query(self, msg, response_msg=None):

        if not response_msg:
            response_msg = msg

        self.send_queue.put_nowait((f'{msg}\r'.encode(), response_msg.encode(), True))

        await asyncio.wait_for(self.no_waiting.wait(), timeout=5)  # some commands, like board resets, take a while

    def send_blind(self, msg):
        self.send_queue.put_nowait((f'{msg}\r'.encode(), None, False))

    def send_and_confirm(self, msg, pause_until):
        self.send_queue.put_nowait((f'{msg}\r'.encode(), pause_until.encode(), False))

    def send_bytes(self, msg):
        self.send_queue.put_nowait((msg, None, False))

    def write_to_port(self, msg):
        # Sends a message as is, without encoding or adding a <CR> character
        if self.port_debug:
            if msg[0] != "W" and msg[0] != "L":  # TODO move to net instance
                self.log.info(f"{self.remote_processor} >>>> {msg}")

        self.writer.write(msg)

    def _parse_msg(self, msg):
        self.received_msg += msg
        self.log.info(f'Parsing message: {msg}')

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            if not msg:
                continue

            # Are we waiting for a confirmation message
            if self.confirm_msg and msg[:len(self.confirm_msg)] == self.confirm_msg:
                self.confirm_msg = None

            # Is a query in progress? If so, if current_message_processor is callable, it's a query
            if not callable(self.current_message_processor) and self.no_waiting.is_set():
                self.send_ready.set()
                continue

            # if not (self.no_waiting and callable(self.current_message_processor)):
            #     continue
            try:
                msg = msg.decode()
            except UnicodeDecodeError:
                self.log.warning(f"Interference / bad data received: {msg}")
                if not self.ignore_decode_errors:
                    raise

            if msg in self.ignored_messages:
                continue

            if callable(self.current_message_processor):
                msg, still_waiting = self.current_message_processor(msg)

            else:
                msg, still_waiting = self.message_processors[msg[:2]](msg)

            if not still_waiting:
                self.current_message_processor = None
                self.no_waiting.set()
                self.send_ready.set()

                # else:
                #     self.platform.process_received_message(msg, self.remote_processor)  # TODO remove?

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
            self.log.info(f"{self.remote_processor} <<<< {resp}")
        return resp

    # async def start_read_loop(self):
    #     """Start the read loop."""
    #     self.log.debug(f" {self} Starting read loop")
    #     self.read_task = self.machine.clock.loop.create_task(self._socket_reader())
    #     self.read_task.add_done_callback(Util.raise_exceptions)

    # async def create_send_task(self):
    #     """Create the send task."""
    #     self.log.debug(f"{self} Creating send task")
    #     self.write_task = self.machine.clock.loop.create_task(self._socket_writer())
    #     self.write_task.add_done_callback(Util.raise_exceptions)

    async def _socket_reader(self):
        while True:
            resp = await self.read(128)
            if resp is None:
                return
            self._parse_msg(resp)

    async def _socket_writer(self):
        while True:
            self.log.info("Waiting for send_queue.")
            res = await self.send_queue.get()
            self.log.info("Got send_queue item: %s", res)

            (msg, pause_until, is_query) = res

            try:
                self.log.info("_socket_write, is send_ready? %s", self.send_ready.is_set())
                await asyncio.wait_for(self.send_ready.wait(), timeout=1)
                self.log.info("Got send_ready.")
            except asyncio.TimeoutError:
                self.log.error("Timeout waiting for send_ready. Message was: %s", msg)
                # TODO Decide what to do here, prob raise a specific exception?
                # self.send_ready.set()  # TODO only if we decide to continue
                raise

            if pause_until:
                self.confirm_msg = pause_until
                self.send_ready.clear()

            if is_query:
                self.no_waiting.clear()

            self.write_to_port(msg)
