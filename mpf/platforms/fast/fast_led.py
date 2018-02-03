"""WS2812 LED on the FAST controller."""
import logging

from typing import Callable, Tuple
from typing import List
from typing import Union

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FASTDirectLED:

    """FAST RGB LED."""

    def __init__(self, number: str, hardware_fade_ms: int) -> None:
        """Initialise FAST LED."""
        self.number = number
        self.dirty = True
        self.hardware_fade_ms = hardware_fade_ms
        self.colors = [0, 0, 0]     # type: List[Union[int, Callable[[int], Tuple[float, int]]]]
        self.log = logging.getLogger('FASTLED')
        # All FAST LEDs are 3 element RGB and are set using hex strings
        self.log.debug("Creating FAST RGB LED at hardware address: %s", self.number)

    @property
    def current_color(self):
        """Return current color."""
        result = ""
        self.dirty = False
        # send this as grb because the hardware will twist it again
        for index in [1, 0, 2]:
            color = self.colors[index]
            if callable(color):
                brightness, fade_ms = color(self.hardware_fade_ms)  # pylint: disable-msg=not-callable
                result += hex(int(brightness * 255))[2:].zfill(2)
                if fade_ms >= self.hardware_fade_ms:
                    self.dirty = True
            else:
                result += "00"

        return result


class FASTDirectLEDChannel(LightPlatformInterface):

    """Represents a single RGB LED channel connected to the Fast hardware platform."""

    def __init__(self, led: FASTDirectLED, channel) -> None:
        """Initialise LED."""
        super().__init__("{}-{}".format(led.number, channel))
        self.led = led
        self.channel = int(channel)

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Set brightness via callback."""
        self.led.dirty = True
        self.led.colors[self.channel] = color_and_fade_callback

    def get_board_name(self):
        """Return the board of this light."""
        return "FAST LED CPU"
