import asyncio
from packaging import version
from typing import Optional
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util

# Minimum firmware versions needed for this module
from mpf.platforms.fast.fast_io_board import FastIoBoard

SEG_MIN_FW = version.parse('0.10')         # Minimum FW for a Segment Display

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

HEX_FORMAT = " 0x%02x"

class FastSegCommunicator:

    """Handles the serial communication to the FAST platform."""

    ignored_messages = ['RX:P',  # RGB Pass
                        'SN:P',  # Network Switch pass
                        'SL:P',  # Local Switch pass
                        'LX:P',  # Lamp pass
                        'PX:P',  # Segment pass
                        'DN:P',  # Network driver pass
                        'DL:P',  # Local driver pass
                        'XX:F',  # Unrecognized command?
                        'R1:F',
                        'L1:P',
                        'GI:P',
                        'TL:P',
                        'TN:P',
                        'XO:P',  # Servo/Daughterboard Pass
                        'XX:U',
                        'XX:N'
                        ]

    __slots__ = ["remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
                 "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
                 "send_queue", "is_retro", "is_legacy", "machine", "platform", "log", "debug", "port", "baud",
                 "xonxoff", "reader", "writer", "read_task"]

    def __init__(self, platform, remote_processor, remote_model, remote_firmware,
                 is_legacy, is_retro, reader, writer):
        """Initialise communicator.

        Args:
        ----
            platform(mpf.platforms.fast.fast.HardwarePlatform): the fast hardware platform
            port: serial port
            baud: baud rate
        """
        self.platform = platform
        self.remote_processor = remote_processor
        self.remote_model = remote_model
        self.remote_firmware = remote_firmware
        self.is_retro = is_retro
        self.is_legacy = is_legacy
        self.max_messages_in_flight = 10
        self.messages_in_flight = 0
        self.ignored_messages_in_flight = {b'-N', b'/N', b'/L', b'-L'}

        self.send_ready = asyncio.Event()
        self.send_ready.set()
        self.write_task = None

        self.received_msg = b''

        self.send_queue = asyncio.Queue()

        self.machine = platform.machine     # type: MachineController

        self.log = self.platform.log
        self.debug = self.platform.config['debug']


        self.reader = reader      # type: Optional[asyncio.StreamReader]
        self.writer = writer      # type: Optional[asyncio.StreamWriter]
        self.read_task = None

    async def init(self):

        self.machine.variables.set_machine_var("fast_{}_firmware".format(self.remote_processor.lower()),
                                               self.remote_firmware)
        '''machine_var: fast_(x)_firmware

        desc: Holds the version number of the firmware for the processor on
        the FAST Pinball controller that's connected. The "x" is replaced with
        either "dmd", "net", or "rgb", one for each processor that's attached.
        '''

        self.machine.variables.set_machine_var("fast_{}_model".format(self.remote_processor.lower()), self.remote_model)

        '''machine_var: fast_(x)_model

        desc: Holds the model number of the board for the processor on
        the FAST Pinball controller that's connected. The "x" is replaced with
        either "dmd", "net", or "rgb", one for each processor that's attached.
        '''

        if self.remote_processor == 'SEG':
            min_version = SEG_MIN_FW
            # latest_version = SEG_LATEST_FW
            self.max_messages_in_flight = 0  # SEG doesn't have ACK messages
        else:
            raise AttributeError(f"Unrecognized FAST processor type: {self.remote_processor}")

        if version.parse(self.remote_firmware) < min_version:
            raise AssertionError(f'Firmware version mismatch. MPF requires the {self.remote_processor} processor '
                                 f'to be firmware {min_version}, but yours is {self.remote_firmware}')

        # Register the connection so when we query the boards we know what responses to expect
        self.platform.register_processor_connection(self.remote_processor, self)

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

    async def reset_net_cpu(self):
        """Reset the NET CPU."""
        self.platform.debug_log('Resetting NET CPU.')
        self.writer.write('BR:\r'.encode())
        msg = ''
        while msg != 'BR:P\r' and not msg.endswith('!B:02\r'):
            msg = (await self.readuntil(b'\r')).decode()
            self.platform.debug_log("Got: %s", msg)

    async def configure_hardware(self):
        """Verify Retro board type."""
        # For Retro boards, send the CPU configuration
        hardware_key = fast_defines.HARDWARE_KEY[self.platform.machine_type]
        self.platform.debug_log("Writing FAST hardware key %s from machine type %s",
                                hardware_key, self.platform.machine_type)
        self.writer.write(f'CH:{hardware_key},FF\r'.encode())

        msg = ''
        while msg != 'CH:P\r':
            msg = (await self.readuntil(b'\r')).decode()
            self.platform.debug_log("Got: %s", msg)

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
        ----
            msg: String of the message you want to send. THe <CR> character will
                be added automatically.

        """
        self.send_queue.put_nowait(msg)

    def _send(self, msg):
        debug = self.platform.config['debug']

        if not self.max_messages_in_flight:  # For processors that don't use this
            self.writer.write(msg.encode() + b'\r')
            self.platform.log.debug("Sending without message flight tracking: %s", msg)
        else:
            self.messages_in_flight += 1
            if self.messages_in_flight > self.max_messages_in_flight:
                self.send_ready.clear()

                self.log.debug("Enabling Flow Control for %s connection. "
                               "Messages in flight: %s, Max setting: %s",
                               self.remote_processor,
                               self.messages_in_flight,
                               self.max_messages_in_flight)

            self.writer.write(msg.encode() + b'\r')
            # Don't log W(atchdog) or L(ight) messages, they are noisy
            if debug and msg[0] != "W" and msg[0] != "L":
                self.platform.log.debug("Send: %s", msg)

    async def _socket_writer(self):
        while True:
            msg = await self.send_queue.get()
            try:
                await asyncio.wait_for(self.send_ready.wait(), 1.0)
            except asyncio.TimeoutError:
                self.log.warning("Port %s was blocked for more than 1s. Resetting send queue! If this happens "
                                 "frequently report a bug!", self.port)
                self.messages_in_flight = 0
                self.send_ready.set()

            self._send(msg)

    def __repr__(self):
        """Return str representation."""
        return f"FAST Communicator attached to {self.remote_processor}"

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
