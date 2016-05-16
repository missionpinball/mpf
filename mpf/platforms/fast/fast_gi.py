import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface


class FASTGIString(GIPlatformInterface):
    def __init__(self, number, sender):
        """A FAST GI string in a WPC machine.

        TODO: Need to implement the enable_relay and control which strings are
        dimmable.
        """
        self.log = logging.getLogger('FASTGIString.0x' + str(number))
        self.number = number
        self.send = sender

    def off(self):
        self.log.debug("Turning Off GI String")
        self.send('GI:' + self.number + ',00')

    def on(self, brightness=255):
        if brightness >= 255:
            brightness = 255

        self.log.debug("Turning On GI String to brightness %s", brightness)
        # self.send('GI:' + self.number + ',' + Util.int_to_hex_string(brightness))

        self.send('GI:{},{}'.format(self.number,
                                    Util.int_to_hex_string(brightness)))