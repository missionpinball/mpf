"""GI on fast."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade


class FASTGIString(LightPlatformSoftwareFade):

    """A FAST GI string in a Retro machine."""

    # __slots__ = ["log", "send"]

    def __init__(self, number, connection, machine, software_fade_ms: int) -> None:
        """initialize GI string."""
        super().__init__(number, machine.clock.loop, software_fade_ms)
        self.log = logging.getLogger('FASTGIString.0x' + str(number))
        self.connection = connection

    def set_brightness(self, brightness: float):
        """Set GI string to a certain brightness."""
        brightness = int(brightness * 255)
        if brightness >= 255:
            brightness = 255

        self.log.debug("Turning On GI String to brightness %s", brightness)
        # self.send_and_forget('GI:' + self.number + ',' + Util.int_to_hex_string(brightness))

        self.connection.send_and_forget('GI:{},{}'.format(self.number,
                                    Util.int_to_hex_string(brightness)))

    def get_board_name(self):
        """Return the board of this light."""
        return "FAST Retro"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        raise AssertionError("Not possible in FASTGI.")

    def get_successor_number(self):
        """Return next number."""
        raise AssertionError("Not possible in FASTGI.")

    def __lt__(self, other):
        """Order lights by string."""
        return self.number < other.number
