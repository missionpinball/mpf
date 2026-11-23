"""FAST Expansion Board Serial Communicator."""
# mpf/platforms/fast/communicators/exp.py

import asyncio
from functools import partial
from typing import TYPE_CHECKING

from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_FEATURES
from mpf.platforms.fast.fast_exp_board import FastExpansionBoard
from mpf.platforms.fast.communicators.base import FastSerialCommunicator, RESPONSE_SETTLE_PASSES

from mpf.core.utility_functions import Util


if TYPE_CHECKING:
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

# Commands a breakout board answers itself while an EB: passthrough is open.
PASSTHROUGH_REPLIES = ('EB:', 'IF:', 'IV:')
# Seconds per reply inside a passthrough session. Measured on a Neuron with FP-PWR-0007 (EXP firmware 0.48,
# power board 0.10): EB:P after 0.3 ms, IF: after 0.7 ms, IV: after 2 ms, a whole session takes ~3.5 ms.
PASSTHROUGH_TIMEOUT = 0.05
# A NUL byte returns from the breakout to the EXP board. Without an open passthrough a bare NUL corrupts
# the next command (the Neuron answers it with XX:F), so the NUL is always sent with its own <CR>: that
# line is answered with XX:F (ignored on EXP) in both cases, and the next command is clean.
PASSTHROUGH_EXIT = b'\x00\r'


class FastExpCommunicator(FastSerialCommunicator):

    """Handles the serial communication for the FAST EXP bus."""

    IGNORED_MESSAGES = ['XX:F']

    __slots__ = ["exp_boards_by_address", "active_board", "_device_processors", "_passthrough_waiters",
                 "passthrough_active"]

    def __init__(self, platform, processor, config):
        """Initialize the EXP communicator."""
        super().__init__(platform, processor, config)

        self.exp_boards_by_address = dict()  # keys = board addresses, values = FastExpansionBoard objects
        self._device_processors = dict()
        self.active_board = None
        self._passthrough_waiters = dict()  # reply header -> future of the running passthrough session
        self.passthrough_active = False

        self.message_processors['BR:'] = self._process_br
        self.message_processors['ER:'] = self._process_er
        for header in PASSTHROUGH_REPLIES:
            self.message_processors[header] = partial(self._process_passthrough_reply, header)

    async def init(self):
        """Query the expansion boards."""
        await self.query_exp_boards()

    def start_tasks(self):
        """Start listening for commands and schedule watchdog."""
        for board in self.exp_boards_by_address.values():
            self.tasks.append(self.platform.machine.clock.schedule_interval(
                              board.update_leds, 1 / board.config['led_hz']))
            for breakout in board.breakouts.values():
                self.tasks.extend(breakout.start_tasks())

    def stopping(self):
        """Stop listening to the board and clear it."""
        for board in self.exp_boards_by_address.values():
            board.communicator.send_and_forget(f'BR@{board.address}:')

    async def soft_reset(self):
        """Trigger a soft reset for the board and all breakouts."""
        for board in self.exp_boards_by_address.values():
            await board.soft_reset()

    async def query_exp_boards(self):
        """Query the EXP bus for connected boards."""
        for board_name, board_config in self.config['boards'].items():

            # normalize model: FP-eXp-0071-2 -> FP-EXP-0071
            board_config['model'] = ('-').join(board_config['model'].split('-')[:3]).upper()

            if board_config['address']:  # need to do it this way since valid config will have 'address' = None
                board_address = board_config['address']
            else:
                board_address = EXPANSION_BOARD_FEATURES[board_config['model']]['default_address']

            # Got an ID for a board that's already registered. This shouldn't happen?
            if board_address in self.exp_boards_by_address:
                raise AssertionError(f'Expansion Board at address {board_address} is already registered')

            board_obj = FastExpansionBoard(board_name, self, board_address, board_config)
            self.exp_boards_by_address[board_address] = board_obj  # registers with this EXP communicator
            self.platform.register_expansion_board(board_obj)  # registers with the platform

            self.active_board = board_address
            self.info_log("Querying EXP board: '%s' on address: %s", board_name, board_address)
            await self.send_and_wait_for_response_processed(f'ID@{board_address}:', 'ID:')

            for breakout_board in board_obj.breakouts.values():
                self.active_board = breakout_board.address
                if not breakout_board.features.get('optional'):
                    await self.send_and_wait_for_response_processed(f'ID@{breakout_board.address}:', 'ID:')
                    continue

                try:
                    await self.send_and_wait_for_response_processed(f'ID@{breakout_board.address}:', 'ID:',
                                                                    max_retries=1)
                except AssertionError:
                    self.log.warning("Optional breakout %s did not answer ID@%s:. MPF will run without it.",
                                     breakout_board, breakout_board.address)

            await board_obj.reset()

    def _process_id(self, msg: str):
        self.exp_boards_by_address[self.active_board[:2]].verify_hardware(msg, self.active_board)
        self.active_board = None
        self.done_processing_msg_response()

    def _process_br(self, msg):
        del msg
        self.active_board = None
        self.done_processing_msg_response()

    def _process_er(self, msg):
        del msg
        self.done_processing_msg_response()

    def send_passthrough(self, breakout, commands, callback):
        """Queue an exclusive passthrough session to a breakout board.

        The session is one entry in the send queue: the writer selects the EXP
        board (EA:), switches the bus through to the breakout (EB:), sends each
        command and waits for its reply, and always leaves the passthrough with
        a NUL byte. Nothing else (e.g. LED updates) is sent in between, since
        the breakout board would receive it instead of the EXP board.

        Parameters
        ----------
            breakout (FastBreakoutBoard): The breakout to talk to
            commands (iterable): Commands like 'IF:'. The reply header must be the same as the command.
            callback (callable): Called with a dict {command: reply payload or None},
                or with None if the passthrough could not be opened.
        """
        self.send_queue.put_nowait((partial(self._run_passthrough, breakout, tuple(commands), callback), None,
                                    f'EB passthrough to {breakout.address}'))

    async def _run_passthrough(self, breakout, commands, callback):
        results = None
        await self._wait_until_idle()
        self.passthrough_active = True
        try:
            self.write_to_port(f'EA:{breakout.expansion_board.address}\r'.encode(),
                               f'EA:{breakout.expansion_board.address}')
            if await self._passthrough_exchange(f'EB:{breakout.index:02X}', 'EB:') == 'P':
                results = dict()
                for command in commands:
                    results[command] = await self._passthrough_exchange(command, command[:3])
        finally:
            self.write_to_port(PASSTHROUGH_EXIT, 'NUL (leave passthrough)')
            self.passthrough_active = False
            self._passthrough_waiters.clear()

        self.machine.clock.loop.call_soon(callback, results)

    async def _wait_until_idle(self):
        """Wait (briefly) until no earlier command is still waiting for its reply."""
        loop = self.machine.clock.loop
        deadline = loop.time() + PASSTHROUGH_TIMEOUT
        while ((not self.no_response_waiting.is_set() or self.pause_sending_flag.is_set()) and
               loop.time() < deadline):
            await asyncio.sleep(.001)

    async def _passthrough_exchange(self, command, reply_header):
        """Send one command inside the passthrough and return the reply payload, or None on timeout."""
        future = self.machine.clock.loop.create_future()
        self._passthrough_waiters[reply_header] = future
        self.write_to_port(f'{command}\r'.encode(), command)

        done, _ = await asyncio.wait([future], timeout=PASSTHROUGH_TIMEOUT)
        if not done:
            # the reply may have arrived in the same loop pass as the timeout
            for _ in range(RESPONSE_SETTLE_PASSES):
                await asyncio.sleep(0)
                if future.done():
                    break

        self._passthrough_waiters.pop(reply_header, None)
        if future.done():
            return future.result()
        future.cancel()
        self.log.debug("No %s reply inside the passthrough", reply_header)
        return None

    def _process_passthrough_reply(self, header, msg):
        future = self._passthrough_waiters.get(header)
        if future and not future.done():
            future.set_result(msg)

    def set_led_fade_rate(self, board_address: str, rate: int) -> None:
        """Sets the hardware LED fade rate for an EXP board.

        Parameters
        ----------
            board_address (str): 2 hex character board address
            rate (int): Fade rate, in milliseconds, between 0 and 8191

        Raises
        ------
            ValueError: If the fade rate is out of bounds
        """
        if not 0 <= rate <= 8191:
            raise ValueError(f"FAST LED fade rate of {rate}ms is out of bounds. Must be between 0 and 8191ms")

        self.platform.debug_log("%s - Setting LED fade rate to %sms", self, rate)
        self.send_and_forget(f'RF@{board_address}:{Util.int_to_hex_string(rate, True)}')

    def register_processor(self, message_prefix, board_address, device_id, callback):
        """Register an exp board processor to handle messages."""
        if message_prefix not in self.message_processors:
            self.message_processors[message_prefix] = partial(self._process_device_msg, message_prefix)
            self._device_processors[message_prefix] = dict()
        if board_address not in self._device_processors[message_prefix]:
            self._device_processors[message_prefix][board_address] = dict()
        self._device_processors[message_prefix][board_address][device_id] = callback

    def _process_device_msg(self, message_prefix, message):
        # Commands like MS: currently don't include the EXP board in the response,
        # so there's no way to know which board needs to be informed. Inform them
        # all? If multiple boards are running concurrently, it'll get ugly.
        device_id = message.split(",")[0]
        for board_callback in self._device_processors[message_prefix].values():
            board_callback[device_id](message)
