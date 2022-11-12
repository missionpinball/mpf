"""FAST Expansion Board."""

from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_BREAKOUT_COUNTS, EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_led import FASTExpLED

class FastExpansionBoard:

    """A FAST Expansion board on the EXP connection."""

    __slots__ = ["communicator", "log", "address", "product_id", "firmware_version", "platform", "breakouts"]

    def __init__(self, communicator, address, product_id, firmware_version):
        """Initialize FastExpansionBoard."""

        self.communicator = communicator
        self.log = communicator.log
        self.address = address
        self.product_id = product_id
        self.firmware_version = firmware_version  # TODO implement min fw version check

        self.log.debug(f"Creating FAST Expansion Board {self.product_id} at address {address}")

        self.platform = communicator.platform

        self.breakouts = list()

        for index in range(EXPANSION_BOARD_BREAKOUT_COUNTS[product_id]):
            brk_board = FastBreakoutBoard(self, index, self.platform, communicator)
            self.breakouts.append(brk_board)
            self.platform.register_breakout_board(brk_board)

    def __repr__(self):
        return f"{self.product_id} @{self.address}"

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}" #TODO add brk

    def set_active(self, address):
        """Set board active."""
        self.communicator.set_active(address)

    async def init(self):
        """Initialize board."""
        for index in range(len(self.breakouts)):
            self.breakouts[index] = FastBreakoutBoard(self, index)

    async def query_breakout_boards(self):
        while True:
            pass

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
            self.platform.register_led_board(self)

    def set_active(self):
        """Set board active."""
        self.communicator.set_active_board(self.address)

    def set_led_fade(self, rate):
        """Set LED fade rate in ms."""

        self.led_fade_rate = rate
        self.communicator.set_led_fade_rate(self.address, rate)
