"""Base class for FAST serial interfaces."""
# mpf/platforms/fast/communicators/base.py

import asyncio

from packaging import version
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE, SerialException

from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util

MIN_FW = version.parse('0.00')  # override in subclass


# pylint: disable-msg=too-many-instance-attributes
class FastSerialCommunicator(LogMixin):

    """Handles the serial communication to the FAST platform."""

    IGNORED_MESSAGES = []

    __slots__ = ["platform", "remote_processor", "config", "writer", "reader", "read_task", "received_msg",
                 "machine", "fast_debug", "port_debug", "remote_firmware", "send_queue", "write_task",
                 "pause_sending_until", "pause_sending_flag", "no_response_waiting", "done_waiting",
                 "ignore_decode_errors", "message_processors", "remote_model", "port", "tasks", "watchdog_cmd"]

    def __init__(self, platform, processor, config):
        """Initialize FastSerialCommunicator."""
        super().__init__()  # Initialize logging
        self.platform = platform
        self.remote_processor = processor.upper()
        self.remote_model = str()
        self.config = config
        self.writer = None
        self.reader = None
        self.tasks = list()  # higher level tasks subclasses might need
        self.read_task = None
        self.write_task = None
        self.received_msg = b''
        self.log = None
        self.machine = platform.machine
        self.fast_debug = platform.debug
        self.port = None  # string of the port we're connected to
        self.port_debug = config['debug']

        # TODO some connections have more than one processor, should there be a processor object?
        self.remote_firmware = None

        self.send_queue = asyncio.Queue()  # Tuples of ( message, pause_until_string)

        self.pause_sending_until = ''
        self.pause_sending_flag = asyncio.Event()
        self.no_response_waiting = asyncio.Event()
        self.done_waiting = asyncio.Event()
        self.no_response_waiting.set()  # Initially, we're not waiting for any response

        self.ignore_decode_errors = True

        self.message_processors = {'XX:': self._process_xx,
                                   'ID:': self._process_id}

        if config.get('watchdog', None):
            self.watchdog_cmd = f"WD:{config['watchdog']:02X}"
        else:
            self.watchdog_cmd = None

        # TODO change these to not be hardcoded
        # TODO do something with the URL endpoint
        self.configure_logging(logger=f'FAST [{self.remote_processor}]', console_level=config['debug'],
                               file_level=config['debug'], url_base='https://fastpinball.com/mpf/error')

    def __repr__(self):
        """Return representation of FAST processor."""
        return f'[FAST {self.remote_processor}]'

    async def soft_reset(self):
        """Trigger a soft reset of the serial communicator."""
        raise NotImplementedError(f"{self.__class__.__name__} does not implement soft_reset()")

    async def connect(self):
        """Connect to the port(s) for this serial interface."""
        for port in self.config['port']:
            # If this is an auto-detect that failed to detect, the port will
            # just be 'auto' and there's no reason to try and connect to it.
            if port == 'auto':
                continue
            self.log.info("Trying to connect to %s at %sbps", port, self.config['baud'])
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
                    self.log.warning("Connection to port %s failed. Will retry.", port)
                else:
                    # we got a connection
                    self.log.info("Connected to %s at %sbps", port, self.config['baud'])
                    self.port = port
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
                self.log.debug("Connected via low latency mode for %s.", self.config['port'])
            except (NotImplementedError, ValueError) as e:
                self.log.debug("Connected via standard mode for %s. %s", self.config['port'], e)

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

    async def init(self):
        """Initialize the communicator with any board-specific logic."""
        raise NotImplementedError(f"{self.__class__.__name__} does not implement init()")

    def _process_xx(self, msg):
        """Process the XX response."""
        self.log.warning("Received XX response:%s", msg)  # what are we going to do here? TODO

    def _process_id(self, msg):
        """Process the ID response."""
        processor, self.remote_model, self.remote_firmware = msg.split()

        if self.remote_processor != processor:
            self._processor_mismatch(processor)
        else:
            self.remote_processor = processor

        self.log.info("Connected to %s with firmware v%s",
                      self.remote_model, self.remote_firmware)

        if version.parse(self.remote_firmware) < MIN_FW:
            raise AssertionError(f'Firmware version mismatch. MPF requires the {self.remote_processor} processor '
                                 f'to be firmware {MIN_FW}, but yours is {self.remote_firmware}')

        self.done_processing_msg_response()

    def _processor_mismatch(self, processor):
        self.error_log(f"PORT CONFIG ERROR: You config lists port '{self.port}' for the {self.remote_processor} "
                       f"connection, but the ID: response shows that port is the {processor} connection. "
                       f"Please update your config.")
        self.machine.stop('FAST Serial port mismatch')

    # pylint: disable-msg=inconsistent-return-statements
    async def readuntil(self, separator, min_chars: int = 0):
        """Read until separator.

        Args:
        ----
            separator: Read until this separator byte.
            min_chars: Minimum message length before separator
        """
        assert self.reader is not None
        buffer = b''
        while True:
            char = await self.reader.readexactly(1)
            buffer += char
            if char == separator and len(buffer) > min_chars:
                if self.port_debug:
                    self.log.info("<<<< %s", buffer)
                return buffer

    def start_watchdog(self):
        """Start listening for commands and schedule watchdog."""
        if self.watchdog_cmd:
            self._watchdog_task()  # send one now
            self.tasks.append(self.machine.clock.schedule_interval(
                self._watchdog_task,
                self.config['watchdog'] / 2000))

    def start_tasks(self):
        """Start periodic tasks, etc.

        Called once on MPF boot, not at game start.
        """

    def stopping(self):
        """The serial connection is about to stop.

        This is called before stop() and allows you to do things that need
        to go out before the connection is closed. A 100ms delay to allow
        for this happens after this is called.
        """

    def cancel_tasks(self):
        """Cancel all outstanding tasks.

        This method is called after stopping()
        """
        for task in self.tasks:
            task.cancel()

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
                    self.log.warning("Event loop stopped before writer could close. "
                                     "This may not be an issue if the event loop was stopped intentionally.")
                else:
                    raise e
            self.writer = None

    async def send_and_wait_for_response(self, msg, pause_sending_until, log_msg=None):
        """Sends a message and awaits until the response is received.

        Parameters
        ----------
            msg (_type_): Message to send
            pause_sending_until (_type_): Response to wait for before sending the next message
            log_msg (_type_, optional): Optional version of the message that will be used in logs.
                Typically used with binary messages so the longs can contain human readable versions.
                Defaults to None which means the actual msg will be used in the logs.
        """
        await self.no_response_waiting.wait()
        self.no_response_waiting.clear()
        self.send_with_confirmation(msg, pause_sending_until, log_msg)

    # pylint: disable-msg=too-many-arguments
    async def send_and_wait_for_response_processed(self, msg, pause_sending_until, timeout=1,
                                                   max_retries=0, log_msg=None):
        """Send a message and wait for the response to be processed.

        Unlike send_and_wait_for_response(), this method will not release the wait when the response is received.
        Instead, the wait must manually be released by calling done_processing_msg_response(). This is useful for
        messages that require multiple responses, or for messages that require real processing where you don't want
        the next messages to be sent until the processing is complete.

        Parameters
        ----------
            msg (_type_): Message to send
            pause_sending_until (_type_): Response to wait for before sending the next message
            timeout (int, optional): The time (in seconds) this communicator will wait for a response.
                If a response is not received by then (based on the pause_sending_until), the message will be resent.
                Defaults to 1.
            max_retries (int, optional): How many times the message will be resent if the response is not
                received by the timeout. -1 means unlimited retries. Defaults to 0.
            log_msg (_type_, optional): Optional version of the message that will be used in logs.
                Typically used with binary messages so the longs can contain human readable versions.
                Defaults to None which means the actual msg will be used in the logs.
        """
        self.done_waiting.clear()

        retries = 0

        while max_retries == -1 or retries <= max_retries:
            try:
                await asyncio.wait_for(self.send_and_wait_for_response(msg, pause_sending_until,
                                                                       log_msg), timeout=timeout)
                break
            except asyncio.TimeoutError:
                self.log.error("Timeout waiting for response to %s. Retrying...", msg)
                retries += 1

        await self.done_waiting.wait()

    def done_processing_msg_response(self):
        """Releases the wait for the response to be processed.

        This is used in conjunction with send_and_wait_for_response_processed().
        May be called safely if there's no wait to release.
        """
        self.done_waiting.set()

    def send_with_confirmation(self, msg, pause_sending_until, log_msg=None):
        """Sends a message without blocking (returns immediately).

        Will hold future messages in the queue until the response is received.

        Parameters
        ----------
            msg (_type_): _description_
            pause_sending_until (_type_): _description_
            log_msg (_type_, optional): _description_. Defaults to None.
        """
        if log_msg:
            self.send_queue.put_nowait((f'{msg}\r'.encode(), pause_sending_until, log_msg))
        else:
            self.send_queue.put_nowait((f'{msg}\r'.encode(), pause_sending_until, msg))

    def send_and_forget(self, msg, log_msg=None):
        """Sends a message and returns immediately without waiting for a response."""
        if log_msg:
            self.send_queue.put_nowait((f'{msg}\r'.encode(), None, log_msg))
        else:
            self.send_queue.put_nowait((f'{msg}\r'.encode(), None, msg))

    def send_bytes(self, msg, log_msg):
        """Send a raw list of bytes to the communicator."""
        # Forcing log_msg since bytes are not human readable
        self.send_queue.put_nowait((msg, None, log_msg))

    def parse_incoming_raw_bytes(self, msg):
        """Parse a bytestring from the serial communicator."""
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

                if self.machine.is_shutting_down:
                    return

                self.log.warning("Interference / bad data received: %s", msg)
                if not self.ignore_decode_errors:
                    raise

            if self.port_debug:
                self.log.info("<<<< %s", msg)

            self._dispatch_incoming_msg(msg)

    def _dispatch_incoming_msg(self, msg):
        # Figures out what to do with incoming messages
        if msg in self.IGNORED_MESSAGES:
            return

        msg_header = msg[:3]
        if msg_header in self.message_processors:
            self.message_processors[msg_header](msg[3:])
            self.no_response_waiting.set()

        # if the msg_header matches the first chars of the self.pause_sending_until, unpause sending
        # Note that the msg_header includes the colon (e.g. "DL:", "SA:") and therefore
        # pause_sending_until must also include the colon.
        if self.pause_sending_flag.is_set() and self.pause_sending_until.startswith(msg_header):
            self._resume_sending()

    def pause_sending(self, msg_header):
        """Pause the sending of serial messages until unblocked."""
        if __debug__:
            assert len(msg_header) >= 3, \
                f"Confirmation headers should be at least three characters, received '{msg_header}'"
        self.pause_sending_until = msg_header
        self.pause_sending_flag.set()

    def _resume_sending(self):
        self.pause_sending_until = None
        self.pause_sending_flag.clear()

    def _watchdog_task(self):
        """Sends the watchdog command."""
        self.send_and_forget(self.watchdog_cmd)

    async def _socket_reader(self):
        # Read coroutine
        while True:
            resp = await self.read(128)
            if resp is None:
                return
            self.parse_incoming_raw_bytes(resp)

    async def read(self, n=-1):
        """Read up to `n` bytes from the stream and log the result if debug is true.

        See :func:`StreamReader.read` for details about read and the `n` parameter.
        """
        try:
            resp = await self.reader.read(n)
        except asyncio.CancelledError:  # pylint: disable-msg=try-except-raise
            raise
        except Exception as e:  # pylint: disable-msg=broad-except
            self.log.warning("Serial error: %s", e)
            return None

        # we either got empty response (-> socket closed) or an error
        if not resp:
            self.log.warning("Serial closed.")
            self.machine.stop("Serial %s closed.", self.config["port"])
            return None

        return resp

    async def _socket_writer(self):
        # Write coroutine
        while True:
            try:
                msg, pause_sending_until, log_msg = await self.send_queue.get()

                if pause_sending_until is not None:
                    self.pause_sending(pause_sending_until)

                # Sends a message
                self.write_to_port(msg, log_msg)

                if self.pause_sending_flag.is_set():
                    await self.pause_sending_flag.wait()

            except SerialException as e:
                self.log.error(e)
                return  # TODO better way to catch shutting down?

    def write_to_port(self, msg, log_msg=None):
        """Send a message as is, without encoding or adding a <CR> character."""
        if self.port_debug:
            if log_msg:
                self.log.info(">>>> %s", log_msg)
            else:
                self.log.info(">>>> %s", msg)

        try:
            self.writer.write(msg)
        except AttributeError:
            self.log.warning("Serial connection is not open. Cannot send message: %s", msg)
            return
