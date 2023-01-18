from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

HEX_FORMAT = " 0x%02x"

MIN_FW = version.parse('0.87') # override in subclass

class FastRgbCommunicator(FastSerialCommunicator):

    """Handles the serial communication for legacy FAST RGB processors including
    the Nano Controller and FP-EXP-0800 LED controller."""

    ignored_messages = []

    def reset(self):
        """Reset the RGB processor."""
        self.send('RF:0')
        self.send('RA:000000')
        self.send(f"RF:{Util.int_to_hex_string(self.config['rgb']['led_fade_time'])}")