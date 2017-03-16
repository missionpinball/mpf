"""GI on fast."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade


class FASTGIString(LightPlatformSoftwareFade):

    """A FAST GI string in a WPC machine."""

    def __init__(self, number, sender, machine, software_fade_ms: int):
        """Initialise GI string."""
        super().__init__(machine.clock.loop, software_fade_ms)
        self.log = logging.getLogger('FASTGIString.0x' + str(number))
        self.number = number
        self.send = sender

    def set_brightness(self, brightness: float):
        """Set GI string to a certain brightness."""
        brightness = int(brightness * 255)
        if brightness >= 255:
            brightness = 255

        self.log.debug("Turning On GI String to brightness %s", brightness)
        # self.send('GI:' + self.number + ',' + Util.int_to_hex_string(brightness))

        self.send('GI:{},{}'.format(self.number,
                                    Util.int_to_hex_string(brightness)))
