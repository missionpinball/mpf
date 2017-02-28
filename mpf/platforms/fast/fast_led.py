"""WS2812 LED on the FAST controller."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FASTDirectLED:

    """FAST RGB LED."""

    def __init__(self, number):
        """Initialise FAST LED."""
        self.number = number
        self.colors = [0, 0, 0]
        self.log = logging.getLogger('FASTLED')
        # All FAST LEDs are 3 element RGB and are set using hex strings
        self.log.debug("Creating FAST RGB LED at hardware address: %s", self.number)

    @property
    def current_color(self):
        """Return current color."""
        return "{0}{1}{2}".format(hex(int(self.colors[0]))[2:].zfill(2),
                                  hex(int(self.colors[1]))[2:].zfill(2),
                                  hex(int(self.colors[2]))[2:].zfill(2))


class FASTDirectLEDChannel(LightPlatformInterface):

    """Represents a single RGB LED channel connected to the Fast hardware platform."""

    def __init__(self, led: FASTDirectLED, channel):
        """Initialise LED."""
        self.led = led
        self.channel = int(channel)

    def set_brightness(self, brightness: float, fade_ms: int):
        """Instantly set this LED channel to the brightness passed."""
        # FAST does not support fade per light/channel
        del fade_ms
        self.led.colors[self.channel] = int(brightness * 255)
