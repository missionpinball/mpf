"""Contains the base classes for FAST expansion and breakout boards"""

import asyncio
from base64 import b16decode
from importlib import import_module

from packaging import version

from mpf.platforms.fast.fast_defines import (BREAKOUT_FEATURES,
                                             EXPANSION_BOARD_FEATURES)


class FastExpansionBoard:

    """A FAST Expansion board on the EXP connection."""

    __slots__ = ["name", "communicator", "config", "platform", "log", "address", "model", "features", "breakouts",
                 "breakouts_with_leds", "_led_task", "firmware_version", "hw_verified", "led_fade_rate"]

    def __init__(self, name: str, communicator, address: str, config: dict) -> None:
        """Initializes a FAST Expansion Board

        Args:
            name (str): Name of this board from the config file
            communicator (FastExpCommunicator): FAST EXP Communicator
            address (str): Two-character hex address of this board
            config (dict): This board's section from the config file

        Raises:
            AssertionError: If a breakout board in the config is not valid.
        """

        self.name = name
        self.communicator = communicator
        self.config = config
        self.platform = communicator.platform
        self.log = communicator.log
        self.address = address
        self.model = config['model']

        self.firmware_version = None
        self.hw_verified = False  # have we made contact with the board and verified it's the right hardware?

        self.log.debug(f'Creating FAST Expansion Board "{self.name}" ({self.model} Address: {self.address})')

        self.features = EXPANSION_BOARD_FEATURES[self.model]  # ([local model numbers,], num of remotes) tuple
        self.breakouts = dict()
        self.breakouts_with_leds = list()
        self._led_task = None  # TODO move to breakout or port and/or mixin class?

        # create the local breakouts
        for idx in range(len(self.features['local_breakouts'])):
            self.create_breakout({'port': str(idx), 'model': self.features['local_breakouts'][idx]})

        # create the remote breakouts
        for brk in self.config['breakouts']:
            if int(brk['port']) > self.features['breakout_ports']:
                # TODO change to config file error
                raise AssertionError(f'Breakout port {brk["port"]} is not available on {self}')

            self.create_breakout(brk)

    def create_breakout(self, config: dict) -> None:
        if BREAKOUT_FEATURES[config['model']].get('device_class'):
            module = import_module('mpf.platforms.fast.fast_exp_board')
            brk_board = module.FastBreakoutBoard(config, self)
        else:
            brk_board = FastBreakoutBoard(config, self)

        self.breakouts[config['port']] = brk_board
        self.platform.register_breakout_board(brk_board)

    def __repr__(self):
        return f'EXP "{self.name}" ({self.model}, @{self.address})'

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}" #TODO add brk

    def verify_hardware(self, id_string: str, active_board: str) -> None:
        """Verifies an EXP or breakout board firmware versions

        Args:
            id_string (str): ID string returned from the ID: FAST Serial Command
            active_board (str): 2 or 3 hex character address of the EXP or BRK board
        """

        self.log.info(f'Verifying hardware for {self} with ID string "{id_string}", board address {active_board}')

        exp_board = active_board[:2]
        brk_board = active_board[2:]  # will be empty if we got a 2-digit address for an EXP board

        try:
            _, product_id, firmware_version = id_string.split()
        except ValueError:
            if id_string == 'F':  # got an ID:F response which means this breakout is not actually there
                self.log.error(f'Breakout {brk_board} on {self} is not responding')
                raise AssertionError(f'Breakout {brk_board} on {self} is not responding')
            else:
                raise AssertionError(f'Invalid ID string {id_string} from {self}')

        assert exp_board == self.address
        self.firmware_version = firmware_version

        if brk_board:
            if version.parse(firmware_version) < version.parse(self.breakouts[brk_board].features['min_fw']):
                self.log.error(f'Firmware on breakout board {product_id} is too old. Required: {self.breakouts[brk_board].features["min_fw"]}, Actual: {firmware_version}. Update at fastpinball.com/firmware')
                self.platform.machine.stop(f'Firmware on breakout board {product_id} is too old. Required: {self.breakouts[brk_board].features["min_fw"]}, Actual: {firmware_version}. Update at fastpinball.com/firmware')

            brk = self.breakouts[brk_board]

            if product_id != brk.model:
                raise AssertionError(f'EXP Board {self}, Breakout Port {brk.index}: Config is set for {brk.model}, but actually found "{id_string}"')
            else:
                brk.hw_verified = True

        else:
            if version.parse(firmware_version) < version.parse(self.features['min_fw']):
                self.log.error(f'Firmware on {self} is too old. Required: {self.features["min_fw"]}, Actual: {firmware_version}. Update at fastpinball.com/firmware')
                self.platform.machine.stop(f'Firmware on {self} is too old. Required: {self.features["min_fw"]}, Actual: {firmware_version}. Update at fastpinball.com/firmware')

            if product_id != self.model:
                raise AssertionError(f"Expected {self.model} but got {id_string} from {self}")
            else:
                self.hw_verified = True

    def start_tasks(self):
        self._update_leds()

        if self.config['led_hz'] > 31.25:
            self.config['led_hz'] = 31.25

        self._led_task = self.platform.machine.clock.schedule_interval(
                        self._update_leds, 1 / self.config['led_hz'])

    def stopping(self):
        if self._led_task:
            self._led_task.cancel()
            self._led_task = None

        self.communicator.send_and_forget(f'BR@{self.address}:')

    async def reset(self):
        await self.communicator.send_and_wait_for_response_processed(f'BR@{self.address}:', 'BR:P')

        # TODO move this to mixin classes for device types?
        if self.config['led_fade_time']:
            self.set_led_fade(self.config['led_fade_time'])

        # TODO re-initialize servos? Or call each breakout to do that?

    async def soft_reset(self):
        for breakout in self.breakouts.values():
            await breakout.soft_reset()

    def _update_leds(self):
        # Called every tick to update the LEDs on this board
        for breakout_address in self.breakouts_with_leds:
            dirty_leds = {k:v.current_color for (k, v) in self.platform.fast_exp_leds.items() if (v.dirty and v.address == breakout_address)}

            if dirty_leds:
                # TODO add the pre-encoded address to the defines file?
                msg_header = ''.join([f'{x:02X}' for x in f'RD@{breakout_address}:'.encode()])  # RD@<address>:, encode to binary then convert to hex chars
                msg = f'{len(dirty_leds):02X}'

                for led_num, color in dirty_leds.items():
                    msg += f'{led_num[3:]}{color}'

                log_msg = f'RD@{breakout_address}:{msg}'  # pretty version of the message for the log

                self.communicator.send_bytes(b16decode(f'{msg_header}{msg}'), log_msg)

    def set_led_fade(self, rate: int) -> None:
        """Set LED fade rate in ms."""

        self.led_fade_rate = rate
        self.communicator.set_led_fade_rate(self.address, rate)


class FastBreakoutBoard:

    """A FAST Breakout board on the EXP connection."""

    __slots__ = ["config", "expansion_board", "log", "index", "platform", "communicator", "address", "features",
                 "leds", "led_fade_rate", "hw_verified", "model"]

    def __init__(self, config, expansion_board):
        """Initialize FastBreakoutBoard."""
        self.config = config
        self.expansion_board = expansion_board  # object
        self.log = expansion_board.log
        self.index = config['port']  # int, zero-based, 0-5
        self.log.debug(f"Creating FAST Breakout Board {self.index} on {self.expansion_board}")
        self.platform = expansion_board.platform
        self.communicator = expansion_board.communicator
        self.address = f'{self.expansion_board.address}{self.index}'  # string hex byte + nibble
        self.features = BREAKOUT_FEATURES[config['model']]
        self.leds = list()  # TODO move to mixin class
        self.led_fade_rate = 0
        self.hw_verified = False

        self.model = self.config['model']

        self.platform.machine.events.add_handler('init_phase_2', self._initialize)

    def __repr__(self):
        return f"Breakout {self.model} on {self.expansion_board}"

    def _initialize(self, **kwargs):
        """Populate the LED objects."""

        # TODO move to a mixin class based on device type

        found = False
        for number, led in self.platform.fast_exp_leds.items():
            if number.startswith(self.address):
                self.leds.append(led)
                found = True

        if found:
            self.expansion_board.breakouts_with_leds.append(self.address)

    async def soft_reset(self):
        """Reset the breakout board."""
        self.communicator.send_and_forget(f'RA@{self.address}:000000')
        await asyncio.sleep(.03)

        # Should we do something with servos? TODO
        # TODO move this to mixin classes for device types?
