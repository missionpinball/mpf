"""A direct light on a fast controller."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface


class FASTMatrixLight(MatrixLightPlatformInterface):

    """A direct light on a fast controller."""

    def __init__(self, number, sender):
        """Initialise light."""
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def off(self):
        """Disable (turn off) this matrix light."""
        # self.send('L1:' + self.number + ',00')
        self.send('L1:{},00'.format(self.number))

    def on(self, brightness=255):
        """Enable (turn on) this driver."""
        if brightness == 0:
            self.off()
            return

        if brightness >= 255:
            brightness = 255

        self.send('L1:{},{}'.format(self.number, Util.int_to_hex_string(brightness)))
