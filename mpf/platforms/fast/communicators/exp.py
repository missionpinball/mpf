import asyncio
from base64 import b16decode
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_exp_board import FastExpansionBoard
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

from mpf.core.utility_functions import Util

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

MIN_FW = version.parse('0.7')

class FastExpCommunicator(FastSerialCommunicator):

    """Handles the serial communication for the FAST EXP bus."""

    ignored_messages = ['XX:F']

    # __slots__ = ["remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
    #              "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
    #              "send_queue", "is_retro", "is_nano", "machine", "platform", "log", "debug", "port", "baud",
    #              "xonxoff", "reader", "writer", "read_task", "boards", "exp_config", "exp_boards", "active_board"]

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.exp_boards = dict()  # keys = board addresses, values = FastExpansionBoard objects
        self.active_board = None
        self._led_task = None

        self.message_processors['BR:'] = self._process_br

    async def init(self):
        # override w/o super because EXP processor does this per-board later

        await self.query_exp_boards()

    def start(self):
        """Start listening for commands and schedule watchdog."""
        self._update_leds()

        if self.config['led_hz'] > 31.25:
            self.config['led_hz'] = 31.25

        self._led_task = self.machine.clock.schedule_interval(
                        self._update_leds, 1 / self.config['led_hz'])

    def stopping(self):
        if self._led_task:
            self._led_task.cancel()
            self._led_task = None

        try:
            for board_address in self.exp_boards.keys():
                self.send_blind(f'BR@{board_address}:')
        except KeyError:
            pass

    def get_address_from_number_string(self, number_str):
        """Return number string."""

        # examples
        # exp-201-i0-b0-p1-1
        # fp-exp-201-i0-b0-p1-1

        stripped_str = number_str.lower().strip('fp-')

        try:
            _, _board, _id, the_rest = stripped_str.split("-", 4)

        except ValueError as e:
            self.platform.raise_config_error(
                    f"Could not parse EXP number {number_str}. Please verify the format.", 7)  # TODO get a real error code

        if the_rest.startswith('b'):
            breakout, device = the_rest.split('-')
        else:
            breakout = 'b0'
            device = the_rest

        _board = _board.zfill(4)  # '201' -> '0201'
        _id = int(_id[1:])  # 'i0' -> 0
        breakout = int(breakout[1:])  # 'b0' -> 0
        device = device  # 'p1-1' -> 'p1-1' or 's1'
        board_address = EXPANSION_BOARD_ADDRESS_MAP[f'{_board}-{_id}'] # '88'

        return board_address, breakout, device

    async def query_exp_boards(self):
        """Query the EXP bus for connected boards."""

        board_count = 0
        for board in self.config['boards']:
            board = board.zfill(6)  # '71-1' --> '0071-1'
            self.active_board = EXPANSION_BOARD_ADDRESS_MAP[board]

            while board_count < len(self.config['boards']):

                await self.send_query(f'ID@{self.active_board}:', 'ID:')

                if len(self.exp_boards) > board_count:
                    self.reset_exp_board(self.active_board)
                    board_count += 1
                    break

    def _process_id(self, msg):
        product_id, firmware_version = msg[3:].split()

        if version.parse(firmware_version) < MIN_FW:
            raise AssertionError(f'Firmware version mismatch. MPF requires the EXP processor '
                                f'to be firmware {MIN_FW}, but yours is {firmware_version}')

        if self.active_board in self.exp_boards:
            # Got an ID for a board that's already registered, which is fine, nothing more to do
            return

        board_obj = FastExpansionBoard(self, self.active_board, product_id, firmware_version)
        self.platform.log.info(f'Registered Expansion board: {product_id}, v{firmware_version}')
        self.exp_boards[self.active_board] = board_obj
        self.platform.register_expansion_board(board_obj)

    def _process_br(self, msg):
        pass  # TODO

    async def reset_exp_board(self, address):
        """Reset an expansion board. Can be 2 or 3 digit hex string."""
        self.send_and_confirm(f'BR@{address}:\r', 'BR:P')

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

    def _update_leds(self):
        for breakout_address in self.platform.exp_breakouts_with_leds:
            dirty_leds = {k:v.current_color for (k, v) in self.platform.fast_exp_leds.items() if (v.dirty and v.address == breakout_address)}

            if dirty_leds:
                hex_count = Util.int_to_hex_string(len(dirty_leds))
                msg = f'52443A{hex_count}'  # RD: in hex 52443A

                for led_num, color in dirty_leds.items():
                    msg += f'{led_num[3:]}{color}'

                self.set_active_board(breakout_address)
                self.send_bytes(b16decode(msg))