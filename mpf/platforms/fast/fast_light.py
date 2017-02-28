"""A direct light on a fast controller."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FASTMatrixLight(LightPlatformInterface):

    """A direct light on a fast controller."""

    def __init__(self, number, sender):
        """Initialise light."""
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def set_brightness(self, brightness: float, fade_ms: int):
        """Enable (turn on) this driver."""
        # FAST gi does not support fades
        del fade_ms
        self.send('L1:{},{}'.format(self.number, Util.int_to_hex_string(int(brightness * 255))))
