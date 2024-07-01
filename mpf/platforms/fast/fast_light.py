"""A direct light on a fast controller."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade


class FASTMatrixLight(LightPlatformSoftwareFade):

    """A direct light on a fast controller."""

    # __slots__ = ["log", "number", "send", "platform"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number, connection, machine, fade_interval_ms: int, platform) -> None:
        """Initialize light."""
        super().__init__(number, machine.clock.loop, fade_interval_ms)
        self.log = logging.getLogger('FASTMatrixLight')
        self.connection = connection
        self.platform = platform

    def set_brightness(self, brightness: float):
        """Set matrix light brightness."""
        self.connection.send_and_forget(f'L1:{self.number},{Util.int_to_hex_string(int(brightness * 255))}')

    def get_board_name(self):
        """Return the board of this light."""
        if self.platform.is_retro:
            return f"FAST Retro ({self.platform.machine_type.upper()})"

        coil_index = 0
        number = Util.hex_string_to_int(self.number)
        for board_obj in self.platform.io_boards.values():
            if coil_index <= number < coil_index + board_obj.driver_count:
                return f"FAST Board {str(board_obj.node_id)}"
            coil_index += board_obj.driver_count

        # fall back if not found
        return "FAST Unknown Board"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        raise AssertionError("Not possible in FASTMatrix.")

    def get_successor_number(self):
        """Return next number."""
        raise AssertionError("Not possible in FASTMatrix.")

    def __lt__(self, other):
        """Order lights by string."""
        return self.number < other.number
