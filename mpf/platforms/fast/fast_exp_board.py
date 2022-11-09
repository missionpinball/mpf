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

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Expansion Board Model: {self.model_string},  Firmware: {self.firmware_version}" #TODO add brk

    def set_active(self, address):
        """Set board active."""
        self.communicator.send(f'EA:{address}')

    async def init(self):
        """Initialize board."""
        for index in range(len(self.breakouts)):
            self.breakouts[index] = FastBreakoutBoard(self, index)

    async def query_breakout_boards(self):
        while True:
            pass


    async def reset_exp_board(self, address):
        """Reset an expansion board."""

        self.platform.debug_log(f'Resetting EXP Board @{address}.')
        self.writer.write(f'BR@{address}:\r'.encode())
        msg = ''
        while msg != 'BR:P\r':
            msg = (await self.readuntil(b'\r')).decode()
            self.platform.debug_log("Got: %s", msg)

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
        self.led_ports = list()

        # TODO this is temporary, change to figure out for real what's on each breakout board.
        for idx in range(4):  # all brk LED are four ports
            self.led_ports.append(FastLEDPort(self, self.address, idx))

        platform.machine.events.add_handler('init_phase_2', self._initialize)

    def _initialize(self, **kwargs):
        """Populate the LED Ports with LED objects."""

        for number, led in self.platform.fast_exp_leds.items():

            led.port_obj.leds[led.index % 32] = led

        for port in self.led_ports:

            # Trim the leading and trailing None values from the LED lists
            first_led = -1
            last_led = -1
            for i in range(32):
                if port.leds[i] is not None:
                    if first_led < 0:
                        first_led = i
                    last_led = i

            port.leds = port.leds[first_led:last_led]

            # Fill in any missing ones with dummies that will have color.
            for i in range(len(port.leds)):
                if port.leds[i] is None:
                    port.leds[i] = FASTDummyLED(f'{port.address}{str(i).zfill(2)}')

    def set_active(self):
        """Set board active."""
        self.communicator.send(f'EA:{self.address}')  # No response expected


class FASTDummyLED:

    def __init__(self, address):
        self.address = address
        self.color = (0, 0, 0)
        self.dirty = False
        self.port_obj = None

class FastLEDPort:

    """A FAST LED port on an expansion board breakout."""

    def __init__(self, breakout_board, address, index):
        """Initialize FastLEDPort."""
        self.breakout = breakout_board  # brk object, TODO
        self.address = address  # string, board address + brk index, byte + nibble
        self.index = index  # 0-3, corresponds to brk LED port index
        self.leds = [None] * 32 # max len 32 (0-31), corresponds to LED index #TODO make this adjustable
        self.dirty = True  # any led in port is dirty  TODO do we need this
        self.lowest_dirty_led = 0  #int
        self.highest_dirty_led = 0  #int

        self.platform = breakout_board.platform

        # TODO
        # when flipping to dirty, also add to platform dirty_led_ports

    def add_led(self, led):
        """Add LED to port."""

        if led.index >= 32:
            raise AssertionError("FAST LED ports can only have 32 LEDs.")
            # TODO add a test and then figure out where this should actually live

    def clear_dirty(self):
        self.lowest_dirty_led = 0
        self.highest_dirty_led = 0
        self.dirty = False

    def set_dirty(self, led_index):
        self.dirty = True

        if led_index < self.lowest_dirty_led:
            self.lowest_dirty_led = led_index
        if led_index > self.highest_dirty_led:
            self.highest_dirty_led = led_index

        self.platform.exp_dirty_led_ports.add(self)

    def flush(self):
        """Flush port."""
        if self.dirty:
            # TODO send data to board
            self.dirty = False
