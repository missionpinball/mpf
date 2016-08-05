"""WS2812 LEDs on the fast controller."""
import logging

from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface


class FASTDirectLED(RGBLEDPlatformInterface):

    """Represents a single RGB LED connected to the Fast hardware platform."""

    def __init__(self, number):
        """Initialise LED."""
        self.log = logging.getLogger('FASTLED')
        self.number = number
        self._current_color = '000000'

        # All FAST LEDs are 3 element RGB and are set using hex strings

        self.log.debug("Creating FAST RGB LED at hardware address: %s",
                       self.number)

    def color(self, color):
        """Instantly set this LED to the color passed.

        Args:
            color: an RGBColor object
        """
        self._current_color = "{0}{1}{2}".format(hex(int(color[0]))[2:].zfill(2),
                                                 hex(int(color[1]))[2:].zfill(2),
                                                 hex(int(color[2]))[2:].zfill(2))

    @property
    def current_color(self):
        """Return current color."""
        return self._current_color
