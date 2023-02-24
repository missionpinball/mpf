"""FAST Expansion Board."""

from base64 import b16decode

from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_FEATURES, EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_led import FASTExpLED

class FastExpansionBoard:

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

        self.breakouts = list()
        self.breakouts_with_leds = list()

        self.features = EXPANSION_BOARD_FEATURES[self.model]
        # led_ports
        # breakout_ports
        # servo_ports

        self._led_task = None  # todo move to breakout or port and/or mixin class?


        for index in range(self.features['breakout_ports'] + 1):  # +1 for the built-in breakout
            brk_board = FastBreakoutBoard(self, index, self.platform, communicator)
            self.breakouts.append(brk_board)
            self.platform.register_breakout_board(brk_board)

    def __repr__(self):
        return f'{self.model} "{self.name}"'

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}" #TODO add brk

    def set_active(self, address):
        """Set board active."""
        self.communicator.set_active(address)

    def verify_hardware(self, id_string, firmware_version):
        """Verify hardware."""

        self.firmware_version = firmware_version

        if id_string != self.model:
            self.log.error(f"Expected {self.model} but got {id_string} from {self}")
            self.hw_verified = False
        else:
            self.hw_verified = True

        return self.hw_verified

    async def init(self):
        """Initialize board."""
        for index in range(len(self.breakouts)):
            self.breakouts[index] = FastBreakoutBoard(self, index)

    # async def query_breakout_boards(self):
    #     while True:
    #         pass

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

    def reset(self):
        self.communicator.send_and_confirm(f'BR@{self.address}:', 'BR:P')

    def _update_leds(self):

        for breakout_address in self.breakouts_with_leds:
            dirty_leds = {k:v.current_color for (k, v) in self.platform.fast_exp_leds.items() if (v.dirty and v.address == breakout_address)}

            if dirty_leds:
                msg = f'52443A{len(dirty_leds):02X}'  # RD: in hex 52443A

                for led_num, color in dirty_leds.items():
                    msg += f'{led_num[3:]}{color}'

                self.communicator.set_active_board(breakout_address)  #TODO use with @ address instead
                self.communicator.send_bytes(b16decode(msg))

class FastBreakoutBoard:

    """A FAST Breakout board on the EXP connection.

        Not really used yet, but will be in the future to track firmware versions on breakouts, wiring connections, etc.
    """

    __slots__ = ["expansion_board", "log", "index", "platform", "communicator", "address", "leds", "led_fade_rate"]

    def __init__(self, expansion_board, index, platform, communicator):
        """Initialize FastBreakoutBoard."""
        self.expansion_board = expansion_board  # object
        self.log = expansion_board.log
        self.log.debug(f"Creating FAST Breakout Board at address {self.expansion_board.address}{index}")
        self.index = index  # int, zero-based, 0-5
        self.platform = platform
        self.communicator = communicator
        self.address = f'{self.expansion_board.address}{self.index}'  # string hex byte + nibble
        self.leds = list()
        self.led_fade_rate = 0

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
