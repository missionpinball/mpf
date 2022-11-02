"""WS2812 LED on the FAST controller."""
import logging

from typing import Optional
from typing import List

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.fast.fast_defines import EXPANSION_BOARD_ADDRESS_MAP

class FASTDirectLED:

    """FAST RGB LED."""

    __slots__ = ["number", "number_int", "dirty", "hardware_fade_ms", "log", "channels", "machine"]

    def __init__(self, number: str, hardware_fade_ms: int, machine) -> None:
        """Initialize FAST LED on RGB processor."""
        self.number_int = int(number)
        self.number = Util.int_to_hex_string(self.number_int)
        self.dirty = True
        self.machine = machine
        self.hardware_fade_ms = hardware_fade_ms
        self.log = logging.getLogger('FASTLED')
        self.channels = [None, None, None]      # type: List[Optional[FASTDirectLEDChannel]]
        # All FAST LEDs are 3 element RGB and are set using hex strings
        self.log.debug("Creating FAST RGB LED at hardware address: %s", self.number)

    def add_channel(self, channel_num: int, channel_obj: "FASTDirectLEDChannel"):
        """Add channel to LED."""
        self.channels[channel_num] = channel_obj

    @property
    def current_color(self):
        """Return current color."""
        result = ""
        self.dirty = False
        current_time = self.machine.clock.get_time()
        # send this as grb because the hardware will twist it again
        for index in [1, 0, 2]:
            channel = self.channels[index]
            if channel:
                brightness, _, done = channel.get_fade_and_brightness(current_time)
                result += hex(int(brightness * 255))[2:].zfill(2)
                if not done:
                    self.dirty = True
            else:
                result += "00"

        return result

class FASTExpLED(FASTDirectLED):

    """FAST RGB LED on an expansion board."""

    # __slots__ = ["board_address", "breakout", "number_int", "number", "dirty", "hardware_fade_ms", "log", "channels", "machine"]

    def __init__(self, number: str, hardware_fade_ms: int, machine) -> None:
        """Initialize FAST LED."""

        # example exp-201-i0-b0-p1-1

        try:
            prefix, board, id, breakout, port, led = number.split("-")

        except ValueError as e:
            machine.platform_controller.raise_config_error(
                    f"Could not parse LED number {number}. Please verify the format.", 7)

        board = board.zfill(4)
        breakout = int(breakout[1:])
        port = int(port[1:]) - 1
        led = int(led) - 1

        self.board_address = EXPANSION_BOARD_ADDRESS_MAP[f'{prefix}-{board}-{id}'] # string hex byte
        self.breakout = breakout # string nibble 0-5
        self.index = (port * 32) + led  # int 0-31
        self.number = f'{self.board_address}{self.breakout}{Util.int_to_hex_string(self.index)}'
        self.dirty = True
        self.machine = machine
        self.hardware_fade_ms = hardware_fade_ms
        self.log = logging.getLogger('FASTLED')
        self.channels = [None, None, None]      # type: List[Optional[FASTDirectLEDChannel]]
        # All FAST LEDs are 3 element RGB and are set using hex strings
        self.log.debug("Creating FAST RGB LED on expansion board at hardware address: %s", self.number)

class FASTDirectLEDChannel(LightPlatformInterface):

    """Represents a single RGB LED channel connected to the FAST hardware platform."""

    __slots__ = ["led", "channel", "_current_fade", "_last_brightness"]

    def __init__(self, led: FASTDirectLED, channel) -> None:
        """Initialise LED."""
        super().__init__("{}-{}".format(led.number, channel))
        self.led = led
        self.channel = int(channel)
        self._current_fade = (0, -1, 0, -1)
        self._last_brightness = None

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Set brightness via callback."""
        self.led.dirty = True
        self._current_fade = (start_brightness, start_time, target_brightness, target_time)
        self._last_brightness = None

    def get_fade_and_brightness(self, current_time):
        """Return fade + brightness and mark as clean if this is it."""
        if self._last_brightness:
            return self._last_brightness, 0, True
        max_fade_ms = self.led.hardware_fade_ms
        start_brightness, start_time, target_brightness, target_time = self._current_fade
        fade_ms = int((target_time - current_time) * 1000.0)
        if fade_ms > max_fade_ms >= 0:
            fade_ms = max_fade_ms
            ratio = ((current_time + (fade_ms / 1000.0) - start_time) /
                     (target_time - start_time))
            brightness = start_brightness + (target_brightness - start_brightness) * ratio
            done = False
        else:
            if fade_ms < 0:
                fade_ms = 0
            brightness = target_brightness
            self._last_brightness = brightness
            done = True

        return brightness, fade_ms, done

    def get_board_name(self):
        """Return the board of this light."""
        return "FAST LED CPU"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.led.number_int * 3 + self.channel == other.led.number_int * 3 + other.channel + 1

    def get_successor_number(self):
        """Return next number."""
        if self.channel == 2:
            return "{}-0".format(self.led.number_int + 1)

        return "{}-{}".format(self.led.number_int, self.channel + 1)

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.led.number_int, self.channel) < (other.led.number_int, other.channel)
