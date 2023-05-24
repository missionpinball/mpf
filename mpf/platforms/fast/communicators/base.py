import asyncio
import functools
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util

MIN_FW = version.parse('0.00') # override in subclass
HAS_UPDATE_TASK = False


def msg_processor(*cmds):
    '''Decorator which will allow a message through that starts with the prefix (or list of prefixes))'''
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, msg):
            cmd, _, rest = msg.partition(':')
            if cmd not in cmds:
                return False
            return await func(self, cmd, rest)
        return wrapper
    return decorator

class FastSerialCommunicator(LogMixin):

    """Handles the serial communication to the FAST platform."""

    ignored_messages = []

    # __slots__ = [] # TODO

    def __init__(self, platform, processor, config):
        """Initialize FastSerialCommunicator."""
        self.platform = platform
        self.remote_processor = processor.upper()
        self.config = config
        self.writer = None
        self.reader = None
        self.read_task = None
        self.received_msg = b''
        self.log = None
        self.machine = platform.machine
        self.fast_debug = platform.debug
        self.port_debug = config['debug']

        self.remote_firmware = None  # TODO some connections have more than one processor, should there be a processor object?

        # self.msg_diverter = asyncio.Event()
        # self.callback_done = asyncio.Event()
        self.send_queue = asyncio.PriorityQueue()  # Tuples of (priority, message, callback)
        self.write_task = None
        # self.msg_diverter_callback = None
        # self.msg_diverter_set = asyncio.Event()

        self.callback_queue = asyncio.Queue()  # Queue for callbacks
        self.callback_done_future = None  # Future for callback completion
        self.callback_stack = list()  # Stack of callbacks who want to process messages

        self.ignore_decode_errors = True  # TODO set to False once the connection is established
        # TODO make this a config option? meh.
        # TODO this is not implemented yet

        self.message_processors = {'XX:': self._process_xx,
                                   'ID:': self._process_id}

        self.configure_logging(logger=f'[{self.remote_processor}]', console_level=config['debug'],
                               file_level=config['debug'], url_base='https://fastpinball.com/mpf/error')
                                # TODO change these to not be hardcoded
                                # TODO do something with the URL endpoint

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    async def soft_reset(self):
        raise NotImplementedError(f"{self.__class__.__name__} does not implement soft_reset()")

    async def connect(self):
        """Does several things to connect to the FAST processor.

        * Opens the serial connection
        * Clears out any data in the serial buffer
        * Starts the read & write tasks
        * Set the flag to ignore decode errors
        """

        for port in self.config['port']:
            self.log.info(f"Trying to connect to {port} at {self.config['baud']}bps")
            success = False

            while not success:
                try:
                    connector = self.machine.clock.open_serial_connection(
                        url=port, baudrate=self.config['baud'], limit=0, xonxoff=False,
                        bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE)
                    self.reader, self.writer = await connector
                except SerialException:
                    if not self.machine.options["production"]:
                        break

                    # if we are in production mode, retry
                    await asyncio.sleep(.1)
                    self.log.warning("Connection to %s failed. Will retry.", port)
                else:
                    # we got a connection
                    self.log.info(f"Connected to {port} at {self.config['baud']}bps")
                    success = True
                    break

            if success:
                break
        else:
            self.log.error("Failed to connect to any of the specified ports.")
            raise SerialException(f"{self} could not connect to a serial port. Is it open in CoolTerm? ;)")

        serial = self.writer.transport.serial
        if hasattr(serial, "set_low_latency_mode"):
            try:
                serial.set_low_latency_mode(True)
                self.log.debug(f"Connected via low latency mode for {self.config['port']}.")
            except (NotImplementedError, ValueError) as e:
                self.log.debug(f"Connected via standard mode for {self.config['port']}. {e}")

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

        self.write_task = asyncio.create_task(self._socket_writer())
        self.write_task.add_done_callback(Util.raise_exceptions)

        self.read_task = asyncio.create_task(self._socket_reader())
        self.read_task.add_done_callback(Util.raise_exceptions)

    async def clear_board_serial_buffer(self):
        """Clear out the serial buffer."""

        self.write_to_port(b'\r\r\r\r')
        # await asyncio.sleep(.5)

    async def init(self):

        await self.send_and_wait('ID:', self._process_id)

    @msg_processor('XX:')
    def _process_xx(self, cmd, msg):
        """Process the XX response."""
        self.log.warning(f"Received XX response: {cmd}:{msg}")  # what are we going to do here? TODO
        return True

    @msg_processor('CH:')
    def process_pass_message(self, cmd, msg):
        if msg == 'P':
            return True
        else:
            self.log.warning(f"Received unexpected pass message: {cmd}:{msg}")
            return True

    @msg_processor('ID:')
    def _process_id(self, cmd, msg):
        """Process the ID response."""
        self.remote_processor, self.remote_model, self.remote_firmware = msg.split()

        self.log.info(f"Connected to {self.remote_model} with firmware v{self.remote_firmware}")

        if version.parse(self.remote_firmware) < MIN_FW:
            raise AssertionError(f'Firmware version mismatch. MPF requires the {self.remote_processor} processor '
                                 f'to be firmware {MIN_FW}, but yours is {self.remote_firmware}')

        return True

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
                    self.log.info(f"<<<< {buffer}")
                return buffer

    def start_tasks(self):
        """Start periodic tasks, etc.

        Called once on MPF boot, not at game start."""

        pass

    def stopping(self):
        """The serial connection is about to stop. This is called before stop() and allows you
        to do things that need to go out before the connection is closed. A 100ms delay to allow for this happens after this is called."""

    def stop(self):
        """Stop and shut down this serial connection."""
        self.log.debug("Stop called on serial connection %s", self.remote_processor)
        if self.read_task:
            self.read_task.cancel()
            self.read_task = None

        if self.write_task:
            self.write_task.cancel()
            self.write_task = None

        if self.writer:
            self.writer.close()
            try:
                self.machine.clock.loop.run_until_complete(self.writer.wait_closed())
            except RuntimeError as e:
                if 'Event loop stopped before Future completed.' in str(e):
                    self.log.warning("Event loop stopped before writer could close. This may not be an issue if the event loop was stopped intentionally.")
                else:
                    raise e
            self.writer = None

    async def send_and_wait(self, msg, callback, priority=1, timeout=1):
        """Sends a message to the remote processor and waits (blocks) until a
        response is received and fully processed.

        The callback needs to release the wait.

        Args:
            msg (_type_): _description_
            callback (_type_, optional): _description_. Defaults to None.
            priority (int, optional): _description_. Defaults to 1.
            timeout (int, optional): _description_. Defaults to 1.

        Raises:
            asyncio.TimeoutError: _description_
        """

        self.send_queue.put_nowait((priority, f'{msg}\r'.encode(), callback))

        if callback is not None:
            # Create a future for callback completion
            self.callback_stack.append(callback)
            self.callback_done_future = self.machine.clock.loop.create_future()

            try:
                await asyncio.wait_for(self.callback_done_future, timeout=timeout)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(f'{self} The serial message {msg} was a query that did not finish after its timeout of {timeout}s.')

    def send_and_forget(self, msg, priority=1):
        self.send_queue.put_nowait((priority, f'{msg}\r'.encode(), None))

    def send_bytes(self, msg, priority=1):
        self.send_queue.put_nowait((priority, msg, None))

    def parse_incoming_raw_bytes(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            if not msg:
                continue

            try:
                msg = msg.decode()
            except UnicodeDecodeError:
                self.log.warning(f"Interference / bad data received: {msg}")
                if not self.ignore_decode_errors:
                    raise

            self.dispatch_incoming_msg(msg)

    def dispatch_incoming_msg(self, msg):

        if msg in self.ignored_messages:
            return

        # Try to pass the message to the most recently registered callback
        while self.callback_stack:
            callback = self.callback_stack[-1]
            if callback(msg):
                # The callback handled the message and wants to remain active
                return
            else:
                # The callback is done, so remove it from the stack
                self.callback_stack.pop()

        # If no callback handled the message, pass it to a message processor
        msg_header = msg[:3]
        if msg_header in self.message_processors:
            self.message_processors[msg_header](msg[3:])
        else:
            self.log.warning(f"Unknown message received: {msg}")

    async def _socket_reader(self):
        # Read coroutine
        while True:
            resp = await self.read(128)
            if resp is None:
                return
            self.parse_incoming_raw_bytes(resp)

            # If there's a callback in the callback_queue, apply it to the message
            if not self.callback_queue.empty():
                callback = await self.callback_queue.get()
                if callback(resp):
                    # If the callback is done, set the result of the future
                    self.callback_done_future.set_result(None)
                else:
                    # If the callback is not done, put it back into the callback_queue
                    await self.callback_queue.put(callback)

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

        # we either got empty response (-> socket closed) or an error
        if not resp:
            self.log.warning("Serial closed.")
            self.machine.stop("Serial {} closed.".format(self.config["port"]))
            return None

        if self.port_debug:
            self.log.info(f"<<<< {resp}")
        return resp

    async def _socket_writer(self):
        # Write coroutine
        while True:
            try:
                _, msg, callback = await self.send_queue.get()

                if callback is not None:
                    # Put the callback into the callback_queue
                    await self.callback_queue.put(callback)

                # Sends a message
                self.write_to_port(msg)

            except:
                return  # TODO better way to catch shutting down?

    def write_to_port(self, msg):
        # Sends a message as is, without encoding or adding a <CR> character
        if self.port_debug:
            self.log.info(f">>>> {msg}")

        try:
            self.writer.write(msg)
        except AttributeError:
            self.log.warning(f"Serial connection is not open. Cannot send message: {msg}")
            return
