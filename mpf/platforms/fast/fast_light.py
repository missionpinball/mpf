"""A direct light on a fast controller."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade


class FASTMatrixLight(LightPlatformSoftwareFade):

    """A direct light on a fast controller."""

    def __init__(self, number, sender, machine, fade_interval_ms: int):
        """Initialise light."""
        super().__init__(machine.clock.loop, fade_interval_ms)
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def set_brightness(self, brightness: float):
        """Set matrix light brightness."""
        self.send('L1:{},{}'.format(self.number, Util.int_to_hex_string(int(brightness * 255))))
