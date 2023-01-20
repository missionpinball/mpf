import asyncio
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_exp_board import FastExpansionBoard
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

from mpf.core.utility_functions import Util

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

HEX_FORMAT = " 0x%02x"

class FastExpCommunicator(FastSerialCommunicator):

    MIN_FW = version.parse('0.7')

    """Handles the serial communication to the FAST platform."""

    ignored_messages = ['XX:F',
                        'BR:P']  # TODO move to... somewhere? SHould this do something?

    # __slots__ = ["remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
    #              "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
    #              "send_queue", "is_retro", "is_nano", "machine", "platform", "log", "debug", "port", "baud",
    #              "xonxoff", "reader", "writer", "read_task", "boards", "exp_config", "exp_boards", "active_board"]

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.exp_boards = dict()  # keys = board addresses, values = FastExpansionBoard objects
        self.active_board = None

    async def init(self):
        # override w/o super because EXP processor does this per-board later

        await self.query_exp_boards()

    async def connect(self):
        """Connect to the serial port."""

        # TODO combine this with the base class and move the extra stuff it does somewhere else


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

        # TODO confirm there's a binary command timeout
        self.platform.debug_log("Connected to FAST processor. Sending 4 CRs to clear buffer.")
        self.send(('\r\r\r'))

    async def query_exp_boards(self):
        """Query the EXP bus for connected boards."""

        # TODO Firmware checking, we require min 0.6
        # Existing fw checks assume only one board per connection, but we need to check each board, so this is a future TODO

        self.platform.debug_log("Verifying connected expansion boards.")

        for board in self.config['boards']:
            msg = ''
            board = board.zfill(6)  # '71-1' --> '0071-1'
            address = EXPANSION_BOARD_ADDRESS_MAP[board]

            while True:

                self.platform.debug_log(f"Querying {board} at address {address}")
                # self.send(f'ID@{address}:')
                self.send(f'ID@{address}:')
                msg = await self._read_with_timeout(.5)

                # ignore XX replies here.
                # TODO this code is duplicated in the serial connector. Refactor
                while msg.startswith('XX:'):
                    msg = await self._read_with_timeout(.5)

                if msg.startswith('ID:EXP'):
                    break

                await asyncio.sleep(.5)

            processor, product_id, firmware_version = msg[3:].split()

            self.platform.log.info(f'Found expansion board {board} at address {address} with processor {processor}, model {product_id}, and firmware {firmware_version}')

            if version.parse(firmware_version) < self.MIN_FW:
                raise AssertionError(f'Firmware version mismatch. MPF requires the EXP processor '
                                 f'to be firmware {self.MIN_FW}, but yours is {firmware_version}')

            await self.reset_exp_board(address)

            board_obj = FastExpansionBoard(self, address, product_id, firmware_version)
            self.exp_boards[address] = board_obj
            self.platform.register_expansion_board(board_obj)

    async def reset_exp_board(self, address):
        """Reset an expansion board."""

        self.send(f'BR@{address}:')
        msg = ''
        while msg != 'BR:P\r':
            msg = await self._read_with_timeout(.5)  # TODO move this after the reader task is started and handle it like a normal message?

    def set_active_board(self, board_address):
        self.active_board = board_address
        self.send(f'EA:{board_address}')

    def set_led_fade_rate(self, board_address, rate):
        if rate > 8191:
            self.log.warning(f"FAST LED fade rate of {rate}ms is too high. Setting to 8191ms")
            rate = 8191
        elif rate < 0:
            self.log.warning(f"FAST LED fade rate of {rate}ms is too low. Setting to 0ms")
            rate = 0

        self.platform.debug_log(f"{self} - Setting LED fade rate to {rate}ms")
        self.send(f'RF@{board_address}:{Util.int_to_hex_string(rate, True)}')
