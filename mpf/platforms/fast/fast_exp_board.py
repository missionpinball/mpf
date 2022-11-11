"""FAST Expansion Board."""

from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_BREAKOUT_COUNTS, EXPANSION_BOARD_ADDRESS_MAP
from mpf.platforms.fast.fast_led import FASTExpLED

class FastExpansionBoard:

    """A FAST Expansion board on the EXP connection."""

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
        # for idx in range(4):  # all brk LED are four ports
        #     self.led_ports.append(FastLEDPort(self, self.address, idx))

        platform.machine.events.add_handler('init_phase_2', self._initialize)

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


# class FastLEDPort:

#     """A FAST LED port on an expansion board breakout."""

#     def __init__(self, breakout_board, address, index):
#         """Initialize FastLEDPort."""
#         self.breakout = breakout_board  # brk object, TODO
#         self.address = address  # string, board address + brk index, byte + nibble
#         self.index = index  # 0-3, corresponds to brk LED port index
#         self.leds = [None] * 32 # max len 32 (0-31), corresponds to LED index #TODO make this adjustable
#         self.dirty = False
#         self.lowest_dirty_led = 0  #int
#         self.highest_dirty_led = 0  #int
#         self.platform = breakout_board.platform

#     def add_led(self, led):
#         """Add LED to port."""

#         if led.index >= 32:
#             raise AssertionError("FAST LED ports can only have 32 LEDs.")
#             # TODO add a test and then figure out where this should actually live

#     def clear_dirty(self):
#         self.lowest_dirty_led = 0
#         self.highest_dirty_led = 0
#         self.dirty = False

#     def set_dirty(self, led_index):

#         if led_index < self.lowest_dirty_led:
#             self.lowest_dirty_led = led_index
#         if led_index > self.highest_dirty_led:
#             self.highest_dirty_led = led_index

#         if not self.dirty:
#             self.lowest_dirty_led = self.highest_dirty_led
#             self.dirty = True

#         self.platform.exp_dirty_led_ports.add(self)
