"""WS2812 LED on the FAST controller."""
import logging

from typing import Optional
from typing import List

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FASTDirectLED:

    """FAST RGB LED."""

    __slots__ = ["number", "dirty", "hardware_fade_ms", "log", "channels", "machine"]

    def __init__(self, number: str, hardware_fade_ms: int, machine) -> None:
        """Initialise FAST LED."""
        self.number = number
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


class FASTDirectLEDChannel(LightPlatformInterface):

    """Represents a single RGB LED channel connected to the Fast hardware platform."""

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
        if fade_ms > max_fade_ms > 0:
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
