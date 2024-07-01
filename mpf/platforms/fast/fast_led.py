"""WS2812 LED on the FAST controller."""
import logging

from typing import Optional
from typing import List

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FASTRGBLED:

    """FAST RGB LED."""

    __slots__ = ["number", "number_int", "dirty", "log", "channels", "machine", "platform", "hardware_fade_ms"]

    def __init__(self, number: str, platform) -> None:
        """Initialize FAST LED on RGB processor."""
        self.number = number  # 5 char hex string, board address, breakout
        self.number_int = int(number, 16)  # Need this for doing math on the number
        self.dirty = True
        self.machine = platform.machine
        self.platform = platform
        self.hardware_fade_ms = 0
        self.log = logging.getLogger('FASTLED')
        self.channels = [None, None, None]      # type: List[Optional[FASTLEDChannel]]
        # All FAST LEDs are 3 element RGB and are set using hex strings
        self.log.debug("Creating FAST RGB LED at hardware address: %s", self.number)

    def add_channel(self, channel_num: int, channel_obj: "FASTLEDChannel"):
        """Add channel to LED."""
        self.channels[channel_num] = channel_obj

    @property
    def current_color(self):
        """Return current color."""
        result = ""
        self.dirty = False
        current_time = self.machine.clock.get_time()
        for index in [0, 1, 2]:
            channel = self.channels[index]
            if channel:
                brightness, _, done = channel.get_fade_and_brightness(current_time)
                result += f'{int(brightness * 255):02X}'
                if not done:
                    self.dirty = True
            else:
                result += "00"

        return result


class FASTExpLED(FASTRGBLED):

    """FAST RGB LED on an expansion board."""

    __slots__ = ["board_address", "breakout_board", "port",
                 "breakout", "index", "address", "exp_board"]

    def __repr__(self):
        """Return representation of this LED."""
        return f'<FASTExpLED: {self.number}>'

    # pylint: disable-msg=super-init-not-called
    def __init__(self, number: str, hardware_fade_ms: int, platform) -> None:
        """Initialize FAST LED."""
        self.number = number  # 5 char hex string, board address, breakout
        self.number_int = int(number, 16)
        self.platform = platform
        self.address = f'{number[0:3]}'  # '880'
        self.exp_board = platform.exp_boards_by_address[self.address[0:2]]
        self.breakout_board = platform.exp_breakout_boards[self.address]

        # self.port = self.port
        self.dirty = False  # we can reset the board on connection so we don't need to send the first color
        self.machine = platform.machine
        self.platform = platform
        self.hardware_fade_ms = hardware_fade_ms
        self.log = logging.getLogger('FASTLED')
        self.channels = [None, None, None]      # type: List[Optional[FASTLEDChannel]]
        # All FAST LEDs are 3 element RGB and are set using hex strings
        self.log.debug("Creating FAST RGB LED on expansion board at hardware address: %s", self.number)


class FASTLEDChannel(LightPlatformInterface):

    """Represents a single RGB LED channel connected to the FAST hardware platform."""

    __slots__ = ["led", "channel", "_current_fade", "_last_brightness"]

    def __repr__(self):
        """Return representation of this LED."""
        return f'<FASTLEDChannel: {self.led.number}-{self.channel}>'

    def __init__(self, led: FASTRGBLED, channel) -> None:
        """Initialize LED."""
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

        # There is a bug that can sometimes cause the start_time to be ahead of the current_time,
        # resulting in a negative brightness value. This may be a floating-point rounding error,
        # or maybe something else. I can't figure it out, so just floor the value to be non-negative.
        if brightness < 0:
            brightness = 0
            self.led.log.warning("Calculated a negative brightness (%s) for led %s channel %s. current_time: %s "
                                 "start_brightness: %s, start_time: %s, target_brightness: %s, target_time: %s",
                                 brightness, self.led, self.channel, current_time, start_brightness, start_time,
                                 target_brightness, target_time)

        return brightness, fade_ms, done

    def get_board_name(self):
        """Return the board of this light."""
        return "FAST LED CPU"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.led.number_int * 3 + self.channel == other.led.number_int * 3 + other.channel + 1

    def get_successor_number(self):
        """Return next number. We want this in the config format."""
        # if self.channel == 2:
        #     hex_int = int(self.number, 16) + 1  # number is hex string so we need to launder it through an int
        #     return f"{hex_int:X}-0"

        # return f"{self.led.number}-{self.channel + 1}"

        if self.channel == 2:
            return f"{self.led.number_int + 1}-0"

        return f"{self.led.number_int}-{self.channel + 1}"

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.led.number_int, self.channel) < (other.led.number_int, other.channel)
