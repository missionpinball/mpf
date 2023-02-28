import asyncio
from base64 import b16decode
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_exp_board import FastExpansionBoard
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

from mpf.core.utility_functions import Util

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

MIN_FW = None  # this is set in the EXP and BRK classes

class FastExpCommunicator(FastSerialCommunicator):

    """Handles the serial communication for the FAST EXP bus."""

    ignored_messages = ['XX:F']

    # __slots__ = ["remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
    #              "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
    #              "send_queue", "is_retro", "is_nano", "machine", "platform", "log", "debug", "port", "baud",
    #              "xonxoff", "reader", "writer", "read_task", "boards", "exp_config", "exp_boards", "active_board"]

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.exp_boards_by_address = dict()  # keys = board addresses, values = FastExpansionBoard objects
        self.active_board = None
        self._led_task = None

        self.message_processors['BR:'] = self._process_br

    async def init(self):
        # override w/o super because EXP processor does this per-board later

        await self.query_exp_boards()

    def start(self):
        """Start listening for commands and schedule watchdog."""

        for board in self.exp_boards_by_address.values():
            board.start()

    def stopping(self):
        for board in self.exp_boards_by_address.values():
            board.stopping()

    async def query_exp_boards(self):
        """Query the EXP bus for connected boards."""

        if self.platform.machine_type == 'neuron' and 'neuron' not in self.config['boards']:

            self.config['boards']['neuron'] = {'model': 'FP-EXP-2000', 'id': '0',}
            self.machine.config_validator.validate_config("fast_exp_board", self.config['boards']['neuron'])

        for board_name, board_config in self.config['boards'].items():

            board_config['model'] = ('-').join(board_config['model'].split('-')[:3]).upper()  # FP-eXp-0071-2 -> FP-EXP-0071

            if not board_config['address']:  # Is there a custom address for this board? If not, look up the default
                board_config['address'] = EXPANSION_BOARD_ADDRESS_MAP[(board_config['model'], board_config['id'])]

            self.active_board = board_config['address']

            if self.active_board in self.exp_boards_by_address:
            # Got an ID for a board that's already registered. This shouldn't happen?
                raise AssertionError(f'Expansion Board at address {self.active_board} is already registered')

            board_obj = FastExpansionBoard(board_name, self, self.active_board, board_config)
            self.exp_boards_by_address[self.active_board] = board_obj  # registers with this EXP communicator
            self.platform.register_expansion_board(board_obj)  # registers with the platform

            await self.send_query(f'ID@{self.active_board}:', 'ID:')

            for breakout_board in board_obj.breakouts.values():
                self.active_board = breakout_board.address
                await self.send_query(f'ID@{self.active_board}:', 'ID:')

            await board_obj.reset()

    def _process_id(self, msg):
        self.exp_boards_by_address[self.active_board[:2]].verify_hardware(msg, self.active_board)

    def _process_br(self, msg):
        pass  # TODO

    def set_active_board(self, board_address):
        """Sets the active board. Can be 2 or 3 digit hex string."""
        if self.active_board != board_address:
            self.log.debug(f"Setting active EXP board to {board_address}")
            self.active_board = board_address
            self.send_blind(f'EA:{board_address}')

    def set_led_fade_rate(self, board_address, rate):
        if rate > 8191:
            self.log.warning(f"FAST LED fade rate of {rate}ms is too high. Setting to 8191ms")
            rate = 8191
        elif rate < 0:
            self.log.warning(f"FAST LED fade rate of {rate}ms is too low. Setting to 0ms")
            rate = 0

        self.platform.debug_log(f"{self} - Setting LED fade rate to {rate}ms")
        self.send_blind(f'RF@{board_address}:{Util.int_to_hex_string(rate, True)}')