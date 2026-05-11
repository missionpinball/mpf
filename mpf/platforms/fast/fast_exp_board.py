"""Contains the base classes for FAST expansion and breakout boards."""

import asyncio
from base64 import b16decode
from binascii import Error as binasciiError
from importlib import import_module

from packaging import version

from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.fast.fast_defines import (BREAKOUT_FEATURES,
                                             EXPANSION_BOARD_FEATURES)


class FastExpansionBoard:

    """A FAST Expansion board on the EXP connection."""

    # pylint: disable-msg=too-many-instance-attributes
    __slots__ = ["name", "communicator", "config", "platform", "log", "address", "model", "features", "breakouts",
                 "breakouts_with_leds", "firmware_version", "hw_verified", "led_fade_rate"]

    def __init__(self, name: str, communicator, address: str, config: dict) -> None:
        """Initializes a FAST Expansion Board.

        Parameters
        ----------
            name (str): Name of this board from the config file
            communicator (FastExpCommunicator): FAST EXP Communicator
            address (str): Two-character hex address of this board
            config (dict): This board's section from the config file

        Raises
        ------
            AssertionError: If a breakout board in the config is not valid.
        """
        self.name = name
        self.communicator = communicator
        self.config = config
        self.platform = communicator.platform
        self.log = communicator.log
        self.address = address
        self.model = config['model']

        self.led_fade_rate = None
        self.firmware_version = None
        self.hw_verified = False  # have we made contact with the board and verified it's the right hardware?

        self.log.debug('Creating FAST Expansion Board "%s" (%s Address: %s)',
                       self.name, self.model, self.address)

        self.features = EXPANSION_BOARD_FEATURES[self.model]  # ([local model numbers,], num of remotes) tuple
        self.breakouts = dict()
        self.breakouts_with_leds = list()

        if self.config['led_hz'] > 31.25:
            self.config['led_hz'] = 31.25

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
        """Define a breakout board within an EXP board."""
        if BREAKOUT_FEATURES[config['model']].get('device_class'):
            module = import_module('mpf.platforms.fast.fast_exp_board')
            brk_board = module.FastBreakoutBoard(config, self)
        else:
            brk_board = FastBreakoutBoard(config, self)

        self.breakouts[config['port']] = brk_board
        self.platform.register_breakout_board(brk_board)

    def __repr__(self):
        """Return representation of this expansion board."""
        return f'EXP "{self.name}" ({self.model}, @{self.address})'

    def get_description_string(self) -> str:
        """Return description string."""
        # TODO add breakout boards
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}"

    def verify_hardware(self, id_string: str, active_board: str) -> None:
        """Verifies an EXP or breakout board firmware versions.

        Parameters
        ----------
            id_string (str): ID string returned from the ID: FAST Serial Command
            active_board (str): 2 or 3 hex character address of the EXP or BRK board
        """
        self.log.info('Verifying hardware for %s with ID string "%s", board address %s',
                      self, id_string, active_board)

        exp_board = active_board[:2]
        brk_board = active_board[2:]  # will be empty if we got a 2-digit address for an EXP board

        try:
            _, product_id, firmware_version = id_string.split()
        except ValueError as e:
            if id_string == 'F':  # got an ID:F response which means this breakout is not actually there
                self.log.error('Breakout %s on %s is not responding', brk_board, self)
                raise AssertionError(f'Breakout {brk_board} on {self} is not responding') from e
            raise AssertionError(f'Invalid ID string {id_string} from {self}') from e

        assert exp_board == self.address
        self.firmware_version = firmware_version

        if brk_board:
            if version.parse(firmware_version) < version.parse(self.breakouts[brk_board].features['min_fw']):
                self.log.error('Firmware on breakout board %s is too old. Required: %s, Actual: %s. '
                               'Update at fastpinball.com/firmware',
                               product_id, self.breakouts[brk_board].features["min_fw"], firmware_version)
                self.platform.machine.stop(f'Firmware on breakout board {product_id} is too old. '
                                           f'Required: {self.breakouts[brk_board].features["min_fw"]}, '
                                           f'Actual: {firmware_version}. Update at fastpinball.com/firmware')

            brk = self.breakouts[brk_board]
            brk.hw_verified = True

        else:
            if version.parse(firmware_version) < version.parse(self.features['min_fw']):
                self.log.error('Firmware on %s is too old. Required: %s, Actual: %s. '
                               'Update at fastpinball.com/firmware',
                               self, self.features["min_fw"], firmware_version)
                self.platform.machine.stop(f'Firmware on {self} is too old. Required: {self.features["min_fw"]}, '
                                           f'Actual: {firmware_version}. Update at fastpinball.com/firmware')

            if product_id != self.model:
                raise ConfigFileError(f"Expected {self.model} but got {id_string} from {self}", 1, self.log.name)
            self.hw_verified = True

    async def reset(self):
        """Send a reset command to the EXP board."""
        await self.communicator.send_and_wait_for_response_processed(f'BR@{self.address}:', 'BR:P')

        # TODO move this to mixin classes for device types?
        if self.config['led_fade_time']:
            self.set_led_fade(self.config['led_fade_time'])

        # TODO re-initialize servos? Or call each breakout to do that?

    async def soft_reset(self):
        """Trigger a 'soft' reset of each breakout board on the EXP."""
        for breakout in self.breakouts.values():
            await breakout.soft_reset()

    def update_leds(self):
        """Look for LEDs that need updating and send to the platform.

        Called every tick to update the LEDs on this board.
        """
        for breakout_address in self.breakouts_with_leds:
            dirty_leds = {k: v.current_color for (k, v) in self.platform.fast_exp_leds.items()
                          if (v.dirty and v.address == breakout_address)}

            if dirty_leds:
                # TODO add the pre-encoded address to the defines file?
                # RD@<address>:, encode to binary then convert to hex chars
                msg_header = ''.join([f'{x:02X}' for x in f'RD@{breakout_address}:'.encode()])
                msg = f'{len(dirty_leds):02X}'

                for led_num, color in dirty_leds.items():
                    msg += f'{led_num[3:]}{color}'

                log_msg = f'RD@{breakout_address}:{msg}'  # pretty version of the message for the log

                try:
                    self.communicator.send_bytes(b16decode(f'{msg_header}{msg}'), log_msg)
                except binasciiError as e:
                    self.log.error(
                        f"Error decoding the following message for board {breakout_address} : {msg_header}{msg}")
                    self.log.info("Attempted update that caused this error: %s", dirty_leds)
                    if not self.config['ignore_led_errors']:
                        raise e

    def set_led_fade(self, rate: int) -> None:
        """Set LED fade rate in ms."""
        self.led_fade_rate = rate
        self.communicator.set_led_fade_rate(self.address, rate)

    def led_port_definition(self, human_readable_port_number):
        """Looks up light port configuration for ports numbered: 1-8, or returns a default fallback."""
        # default configuration
        port_information = {
            'port': human_readable_port_number,
            'type': 'ws2812',
            'count': 32,
            'rgbw_override_indexes': None
        }

        led_port_configs = self.config['led_ports']
        if len(led_port_configs) > 0:
            for port_config in led_port_configs:
                if int(port_config['port']) == int(human_readable_port_number):
                    port_type = port_config['type']
                    port_information['type'] = port_type
                    port_information['count'] = port_config['count']

                    if port_type == 'mixed':
                        zero_based_indexes = [idx - 1 for idx in port_config['rgbw_numbers']]
                        port_information['rgbw_override_indexes'] = zero_based_indexes

                    break

        return port_information

    def light_count_on_port(self, human_readable_port_number):
        """Looks up the number of lights configured to be on a certain light port: 1-8."""
        return self.led_port_definition(human_readable_port_number)['count']


class FastBreakoutBoard:

    """A FAST Breakout board on the EXP connection."""

    __slots__ = ["config", "expansion_board", "log", "index", "platform", "communicator", "address", "features",
                 "leds", "led_fade_rate", "hw_verified", "model"]

    def __init__(self, config, expansion_board):
        """Initialize FastBreakoutBoard."""
        self.config = config
        self.expansion_board = expansion_board  # object
        self.log = expansion_board.log
        self.index = int(config['port'])  # int, zero-based, 0-5
        self.log.debug("Creating FAST Breakout Board %s on %s", self.index, self.expansion_board)
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
        """Return representation of the breakout board."""
        return f"Breakout {self.model} @{self.address} on {self.expansion_board}"

    def _initialize(self, **kwargs):
        """Populate the LED objects."""
        del kwargs
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
        if self.features.get('led_ports'):
            self.communicator.send_and_forget(f'RA@{self.address}:000000')
            await asyncio.sleep(.03)

            self._configure_led_headers()

        # Should we do something with servos? TODO
        # TODO move this to mixin classes for device types?

    def _led_ports(self):
        port_count = self.features.get('led_ports')
        if port_count:
            return [self._led_port(internal_port_number) for internal_port_number in range(port_count)]
        return None

    def _led_port(self, internal_port_number):
        human_readable_port_number = self.index * 4 + internal_port_number + 1
        return self.expansion_board.led_port_definition(human_readable_port_number)

    def _configure_led_headers(self):
        leds_available = 128
        next_address = 0
        for port in self._led_ports():
            human_readable_port_number = port['port']
            internal_port_number = (human_readable_port_number - 1) % 4
            port_type = port['type']
            count = port['count']
            if count <= leds_available:
                mixed_rgbw_offsets = port['rgbw_override_indexes']
                self._configure_led_header(internal_port_number, port_type, next_address, count, mixed_rgbw_offsets)
                leds_available -= count
                next_address += count
            else:
                raise ConfigFileError(f"Port {human_readable_port_number} exceeds LED limit of 128."
                                      "Previously used: {128-leds_available} Additional requested: {count}",
                                      2, self.log.name)

    # pylint: disable-msg=too-many-arguments
    def _configure_led_header(self, port_number, port_type, offset, light_count, mixed_override_offsets):
        """Command: ER - @ Breakout address : port 0-3, type #, starting LED # hex, count hex[, rgbw-unit-address].

        Fresh board state is equivalent to ER:0,0,0,20  ER:1,0,20,20 etc
        The rgb-unit-address is any additional hex address numbers for a mixed chain where the unit should be set
        to the command type (arg#2).
        These addresses are based on the first address in the chain, so 0 means the same in the overall 128 light
        address space as the offset_hex value
        """
        type_number = {
            'ws2182': 0,
            'sk6812': 1,
            'mixed': 2,
            'apa102': 3,
        }.get(port_type, 0)

        count_hex = Util.int_to_hex_string(light_count)
        offset_hex = Util.int_to_hex_string(offset)
        rgbw_overrides = ''  # Future: empty if none, else a comma and a list of hex addresses separated by commas
        if port_type == 'mixed' and mixed_override_offsets:
            for override_offset in mixed_override_offsets:
                rgbw_overrides += f',{Util.int_to_hex_string(override_offset)}'

        message = f'ER@{self.address}:{port_number},{type_number},{offset_hex},{count_hex}{rgbw_overrides}'
        self.log.debug("Sending LED port config to breakout. %s", message)
        self.communicator.send_with_confirmation(message, 'ER:P')
