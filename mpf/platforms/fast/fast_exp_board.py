"""FAST Expansion Board."""

from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_BREAKOUT_COUNTS

class FastExpansionBoard:

    """A FAST Expansion board on the EXP connection."""

    def __init__(self, communicator, address, model_string, firmware_version):
        """Initialize FastExpansionBoard."""

        self.communicator = communicator

        self.address = address
        self.model_string = model_string
        self.firmware_version = firmware_version

        self.breakouts = [None] * EXPANSION_BOARD_BREAKOUT_COUNTS[model_string]

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}" #TODO add brk

    def set_active(self, address):
        """Set board active."""
        self.communicator.send(f'EA:{address}')


class FastBreakoutBoard:

    """A FAST Breakout board on the EXP connection.

        Not really used yet, but will be in the future to track firmware versions on breakouts, wiring connections, etc.
    """

    def __init__(self, expansion_board, index):
        """Initialize FastBreakoutBoard."""
        self.expansion_board = expansion_board  # object
        self.index = index  # int, zero-based, 0-5
        self.address = f'{self.expansion_board.address}{self.index}'  # string hex byte + nibble
        self.led_ports = list(None, None, None, None) # type: Dict[str(address+brk nibble), FastLedPort]
        # all brk LED are four ports

    def set_active(self):
        """Set board active."""
        self.expansion_board.set_active(self.address)

class FastLEDPort:

    """A FAST LED port on an expansion board breakout."""

    def __init__(self, breakout_board, address, index):
        """Initialize FastLEDPort."""
        self.breakout = breakout_board  # brk object, TODO
        self.address = address  # string, board address + brk index, byte + nibble
        self.index = index  # 0-3, corresponds to brk LED port index
        self.leds = list() # max len 32 (0-31), corresponds to LED index
        self.dirty = True  # any led in port is dirty  TODO do we need this
        self.lowest_dirty_led = 0  #int
        self.highest_dirty_led = 0  #int

        # TODO
        # when flipping to dirty, also add to platform dirty_led_ports

    def add_led(self, led):
        """Add LED to port."""

        if led.index >= 32:
            raise AssertionError("FAST LED ports can only have 32 LEDs.")
            # TODO add a test and then figure out where this should actually live

    def flush(self):
        """Flush port."""
        if self.dirty:
            # TODO send data to board
            self.dirty = False