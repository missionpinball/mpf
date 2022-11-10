import asyncio
from packaging import version
from typing import Optional
from mpf.platforms.fast.fast_serial_communicator import FastSerialCommunicator
from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_exp_board import FastExpansionBoard

from mpf.core.utility_functions import Util

# Minimum firmware versions needed for this module
from mpf.platforms.fast.fast_io_board import FastIoBoard

EXP_MIN_FW = version.parse('0.10')

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

HEX_FORMAT = " 0x%02x"

class FastExpCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    ignored_messages = ['XX:F',]

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
        self.exp_config = self.platform.config['expansion_boards']
        self.remote_processor = 'EXP'

        # self.max_messages_in_flight = 10
        # self.messages_in_flight = 0
        # self.ignored_messages_in_flight = {b'-N', b'/N', b'/L', b'-L'}
        self.exp_boards = dict()  # keys = board addresses, values = FastExpansionBoard objects
        self.led_ports = set()  # set of LED port objects
        # this is a set since if a port doesn't have any LEDs attached then we want it to not exist in our world

        self.send_ready = asyncio.Event()
        self.send_ready.set()
        self.write_task = None
        self.read_task = None
        self.received_msg = b''
        self.active_board = None
        self.send_queue = asyncio.Queue()

    async def init(self):

        # Register the connection so when we query the boards we know what responses to expect
        self.platform.register_processor_connection('EXP', self)

        # await self.reset_exp_cpu()

        await self.query_exp_boards()

        self.write_task = self.machine.clock.loop.create_task(self._socket_writer())
        self.write_task.add_done_callback(Util.raise_exceptions)

        return self

    def __repr__(self):
        """Return str representation."""
        return "FAST EXP Communicator"

    async def query_exp_boards(self):
        """Query the EXP bus for connected boards."""

        # TODO Firmware checking
        # Existing fw checks assume only one board per connection, but we need to check each board, so this is a future TODO

        self.platform.debug_log("Verifying connected expansion boards.")

        for board in self.exp_config:

            while True:

                board = board.zfill(6)  # '71-1' --> '0071-1'
                address = EXPANSION_BOARD_ADDRESS_MAP[board]

                self.platform.debug_log(f"Querying {board} at address {address}")
                self.writer.write(f'ID@{address}:\r'.encode())
                msg = await self._read_with_timeout(.5)

                # ignore XX replies here.
                # TODO this code is duplicated in the serial connector. Refactor
                while msg.startswith('XX:'):
                    msg = await self._read_with_timeout(.5)

                if msg.startswith('ID:'):
                    break

                await asyncio.sleep(.5)

            processor, product_id, firmware_version = msg[3:].split()

            self.platform.log.info(f'Found expansion board {board} at address {address} with processor {processor}, model {product_id}, and firmware {firmware_version}')

            board_obj = FastExpansionBoard(self, address, product_id, firmware_version)
            self.exp_boards[address] = board_obj
            self.platform.register_expansion_board(board_obj)

    def set_active_board(self, board_address):
        self.active_board = board_address
        self.send(f'EA:{board_address}')
        # self.writer.write(f'EA:{board_address}\r'.encode())

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
        ----
            msg: String of the message you want to send. THe <CR> character will
                be added automatically.

        """
        # self.platform.debug_log("EXP send: %s", msg)
        self.send_queue.put_nowait(msg)

    def _send(self, msg):

        # TODO for now EXP bus will not track any messages. If there are ones we want
        # to track in the future (maybe?), we can add here

        self.writer.write(msg.encode() + b'\r')

    async def _socket_writer(self):
        while True:
            msg = await self.send_queue.get()
            # try:
            #     await asyncio.wait_for(self.send_ready.wait(), 1.0)
            # except asyncio.TimeoutError:
            #     self.log.warning("Port %s was blocked for more than 1s. Resetting send queue! If this happens "
            #                      "frequently report a bug!", self.port)
            #     self.send_ready.set()
            a = 1

            self._send(msg)

    def _parse_msg(self, msg):
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

    async def _read_with_timeout(self, timeout):
        try:
            msg_raw = await asyncio.wait_for(self.readuntil(b'\r'), timeout=timeout)
        except asyncio.TimeoutError:
            return ""
        return msg_raw.decode()
