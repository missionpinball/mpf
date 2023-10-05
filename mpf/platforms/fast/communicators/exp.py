from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_FEATURES
from mpf.platforms.fast.fast_exp_board import FastExpansionBoard
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

from mpf.core.utility_functions import Util

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

class FastExpCommunicator(FastSerialCommunicator):

    """Handles the serial communication for the FAST EXP bus."""

    IGNORED_MESSAGES = ['XX:F']

    __slots__ = ["exp_boards_by_address", "active_board", "_led_task"]

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.exp_boards_by_address = dict()  # keys = board addresses, values = FastExpansionBoard objects
        self.active_board = None
        self._led_task = None

        self.message_processors['BR:'] = self._process_br

    async def init(self):
        await self.query_exp_boards()

    def start_tasks(self):
        """Start listening for commands and schedule watchdog."""

        for board in self.exp_boards_by_address.values():
            board.start_tasks()

    def stopping(self):
        for board in self.exp_boards_by_address.values():
            board.stopping()

    async def soft_reset(self):
        for board in self.exp_boards_by_address.values():
            await board.soft_reset()

    async def query_exp_boards(self):
        """Query the EXP bus for connected boards."""

        for board_name, board_config in self.config['boards'].items():

            board_config['model'] = ('-').join(board_config['model'].split('-')[:3]).upper()  # FP-eXp-0071-2 -> FP-EXP-0071

            if board_config['address']:  # need to do it this way since valid config will have 'address' = None
                board_address = board_config['address']
            else:
                board_address = EXPANSION_BOARD_FEATURES[board_config['model']]['default_address']

            if board_address in self.exp_boards_by_address:
            # Got an ID for a board that's already registered. This shouldn't happen?
                raise AssertionError(f'Expansion Board at address {board_address} is already registered')

            board_obj = FastExpansionBoard(board_name, self, board_address, board_config)
            self.exp_boards_by_address[board_address] = board_obj  # registers with this EXP communicator
            self.platform.register_expansion_board(board_obj)  # registers with the platform

            self.active_board = board_address
            await self.send_and_wait_for_response_processed(f'ID@{board_address}:', 'ID:')

            for breakout_board in board_obj.breakouts.values():
                self.active_board = breakout_board.address
                await self.send_and_wait_for_response_processed(f'ID@{breakout_board.address}:', 'ID:')

            await board_obj.reset()

    def _process_id(self, msg: str):
        self.exp_boards_by_address[self.active_board[:2]].verify_hardware(msg, self.active_board)
        self.active_board = None
        self.done_processing_msg_response()

    def _process_br(self, msg):
        del msg
        self.active_board = None
        self.done_processing_msg_response()

    def set_led_fade_rate(self, board_address: str, rate: int) -> None:
        """Sets the hardware LED fade rate for an EXP board

        Args:
            board_address (str): 2 hex character board address
            rate (int): Fade rate, in milliseconds, between 0 and 8191

        Raises:
            ValueError: If the fade rate is out of bounds
        """
        if not 0 <= rate <= 8191:
            raise ValueError(f"FAST LED fade rate of {rate}ms is out of bounds. Must be between 0 and 8191ms")

        self.platform.debug_log(f"{self} - Setting LED fade rate to {rate}ms")
        self.send_and_forget(f'RF@{board_address}:{Util.int_to_hex_string(rate, True)}')
