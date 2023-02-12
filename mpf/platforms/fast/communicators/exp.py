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
        self._led_task = None

    async def init(self):
        # override w/o super because EXP processor does this per-board later

        await self.query_exp_boards()

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
                # self.send_blind(f'ID@{address}:')
                self.write_to_port(f'ID@{address}:\r'.encode())
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

            if version.parse(firmware_version) < MIN_FW:
                raise AssertionError(f'Firmware version mismatch. MPF requires the EXP processor '
                                 f'to be firmware {MIN_FW}, but yours is {firmware_version}')

            await self.reset_exp_board(address)

            board_obj = FastExpansionBoard(self, address, product_id, firmware_version)
            self.exp_boards[address] = board_obj
            self.platform.register_expansion_board(board_obj)

    async def reset_exp_board(self, address):
        """Reset an expansion board."""

        self.write_to_port(f'BR@{address}:\r'.encode())
        msg = ''
        while msg != 'BR:P\r':
            msg = await self._read_with_timeout(.5)  # TODO move this after the reader task is started and handle it like a normal message?

    def set_active_board(self, board_address):

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

    def start(self):
        """Start listening for commands and schedule watchdog."""
        self._update_leds()

        if self.config['led_hz'] > 31.25:
            self.config['led_hz'] = 31.25

        self._led_task = self.machine.clock.schedule_interval(
                        self._update_leds, 1 / self.config['led_hz'])

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

    def stopping(self):
        if self._led_task:
            self._led_task.cancel()
            self._led_task = None

        try:
            for board_address in self.exp_boards.keys():
                self.send_blind(f'BR@{board_address}:')
        except KeyError:
            pass
