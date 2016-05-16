import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface


class FASTMatrixLight(MatrixLightPlatformInterface):

    def __init__(self, number, sender):
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def off(self):
        """Disables (turns off) this matrix light."""
        # self.send('L1:' + self.number + ',00')
        self.send('L1:{},00'.format(self.number))

    def on(self, brightness=255):
        """Enables (turns on) this driver."""
        if brightness == 0:
            self.off()
            return

        if brightness >= 255:
            brightness = 255

        self.send('L1:{},{}'.format(self.number, Util.int_to_hex_string(brightness)))