"""FAST Expansion Board."""

class FastExpBoard:

    """A FAST Expansion board on the EXP connection."""

    def __init__(self, communicator):
        """Initialize FastExpBoard."""

        self.communicator = communicator

        self.address = None
        self.model_string = None
        self.firmware_version = None

        self.breakouts = dict() # type: Dict[int, FastBreakout]


    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}"

    def add_led_port(self, port):
        """Add LED port."""
        self.led_ports[port.address] = port

    def set_active(self):
        """Set board active."""
        pass

        # send EA:{address}

class FastBreakoutBoard:

    """A FAST Breakout board on the EXP connection.

        Not really used yet, but will be in the future to track firmware versions on breakouts, wiring connections, etc.
    """

    def __init__(self, expansion_board, index):
        """Initialize FastBreakoutBoard."""
        self.expansion_board = expansion_board  # object
        self.index = index  # int, zero-based, 0-5
        self.led_ports = dict() # type: Dict[str(address+brk nibble), FastLedPort]


class FastLEDPort:

    """A FAST LED port on an expansion board breakout."""

    def __init__(self, address, index):
        """Initialize FastLEDPort."""
        self.address = address  # string, board address + brk index, byte + nibble
        self.index = index
        self.leds = list() # max len 32 (0-31), corresponds to LED index
        self.dirty = True
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