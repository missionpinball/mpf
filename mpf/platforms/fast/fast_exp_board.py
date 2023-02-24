"""FAST Expansion Board."""

from base64 import b16decode
from importlib import import_module
from packaging import version

from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_BREAKOUTS, BREAKOUT_FEATURES, EXP_BREAKOUT_0_IDS
from mpf.platforms.fast.fast_led import FASTExpLED

class FastExpansionBoard:

    MIN_FW = version.parse('0.7')

    """A FAST Expansion board on the EXP connection."""

    # __slots__ = ["communicator", "log", "address", "model", "firmware_version", "platform", "breakouts"]

    def __init__(self, name, communicator, address, config):
        """Initialize FastExpansionBoard."""

        self.name = name
        self.communicator = communicator
        self.config = config
        self.platform = communicator.platform
        self.log = communicator.log
        self.address = address
        self.model = config['model']
        self.id = config['id']

        self.firmware_version = None
        self.hw_verified = False  # have we made contact with the board and verified it's the right hardware?

        self.log.debug(f'Creating FAST Expansion Board "{self.name}" ({self.model} ID {self.id})')

        self.num_breakouts = EXPANSION_BOARD_BREAKOUTS[self.model]
        self.breakouts = dict()
        self.breakouts_with_leds = list()
        self._led_task = None  # todo move to breakout or port and/or mixin class?

        self.create_breakout({'port': '0', 'model': self.model})

        for brk in self.config['breakouts']:
            if brk:
                self.create_breakout(brk)

    def create_breakout(self, config):
        if BREAKOUT_FEATURES[config['model']].get('device_class'):
            # module = import_module(BREAKOUT_FEATURES[config['model']]['device_class'])
            module = import_module('mpf.platforms.fast.fast_exp_board')
            brk_board = module.FastBreakoutBoard(config, self)
        else:
            brk_board = FastBreakoutBoard(config, self)

        self.breakouts[config['port']] = brk_board
        self.platform.register_breakout_board(brk_board)

    def __repr__(self):
        return f'{self.model} "{self.name}"'

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}" #TODO add brk

    def set_active(self, address):
        """Set board active."""
        self.communicator.set_active(address)

    def verify_hardware(self, id_string, active_board):
        """Verify hardware."""

        exp_board = active_board[:2]
        brk_board = active_board[2:]
        proc, product_id, firmware_version = id_string.split()

        assert exp_board == self.address

        if proc == 'EXP':

            self.firmware_version = firmware_version

            if product_id != self.model:
                raise AssertionError(f"Expected {self.model} but got {id_string} from {self}")
            else:
                self.hw_verified = True

        elif proc in ('BRK', 'LED'):

            brk = self.breakouts[brk_board]

            if product_id != brk.model:
                raise AssertionError(f"Expected {brk.model} but got {id_string} from {self}")
            else:
                brk.hw_verified = True

        else:
            raise AssertionError(f'Unknown processor type {proc} in ID response')

    def start(self):
        self._update_leds()

        if self.config['led_hz'] > 31.25:
            self.config['led_hz'] = 31.25

        self._led_task = self.platform.machine.clock.schedule_interval(
                        self._update_leds, 1 / self.config['led_hz'])

    def stopping(self):
        if self._led_task:
            self._led_task.cancel()
            self._led_task = None

        self.communicator.send_blind(f'BR@{self.address}:')

    async def reset(self):
        await self.communicator.send_query(f'BR@{self.address}:', 'BR:P')

    def _update_leds(self):

        for breakout_address in self.breakouts_with_leds:
            dirty_leds = {k:v.current_color for (k, v) in self.platform.fast_exp_leds.items() if (v.dirty and v.address == breakout_address)}

            if dirty_leds:
                msg = f'52443A{len(dirty_leds):02X}'  # RD: in hex 52443A

                for led_num, color in dirty_leds.items():
                    msg += f'{led_num[3:]}{color}'

                self.communicator.set_active_board(breakout_address)  # TODO use with @ address instead
                self.communicator.send_bytes(b16decode(msg.upper()))  # TODO I feel like upper() is a back, look into how colors are coming through in lower

class FastBreakoutBoard:

    """A FAST Breakout board on the EXP connection.

        Not really used yet, but will be in the future to track firmware versions on breakouts, wiring connections, etc.
    """

    # __slots__ = ["expansion_board", "log", "index", "platform", "communicator", "address", "leds", "led_fade_rate"]

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
        self.leds = list()
        self.led_fade_rate = 0
        self.hw_verified = False

        if self.index == '0':  # Built in breakout 0 boards may have different models than their parent expansion boards
            self.model = EXP_BREAKOUT_0_IDS[self.config['model']]
        else:
            self.model = self.config['model']

        # TODO this is temporary, change to figure out for real what's on each breakout board.

        self.platform.machine.events.add_handler('init_phase_2', self._initialize)

    def __repr__(self):
        return f"Breakout {self.index}, on {self.expansion_board}"

    def _initialize(self, **kwargs):
        """Populate the LED objects."""

        found = False
        for number, led in self.platform.fast_exp_leds.items():
            if number.startswith(self.address):
                self.leds.append(led)
                found = True

        if found:
            self.expansion_board.breakouts_with_leds.append(self.address)

    def set_active(self):
        """Set board active."""
        self.communicator.set_active_board(self.address)

    def set_led_fade(self, rate):
        """Set LED fade rate in ms."""

        self.led_fade_rate = rate
        self.communicator.set_led_fade_rate(self.address, rate)

    async def query_breakout_boards(self):
        """Query breakout boards."""



        await self.send_query(f'ID@{self.active_board}:', 'ID:')