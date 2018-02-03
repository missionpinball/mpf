"""A direct light on a fast controller."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade


class FASTMatrixLight(LightPlatformSoftwareFade):

    """A direct light on a fast controller."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number, sender, machine, fade_interval_ms: int, platform) -> None:
        """Initialise light."""
        super().__init__(number, machine.clock.loop, fade_interval_ms)
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender
        self.platform = platform

    def set_brightness(self, brightness: float):
        """Set matrix light brightness."""
        self.send('L1:{},{}'.format(self.number, Util.int_to_hex_string(int(brightness * 255))))

    def get_board_name(self):
        """Return the board of this light."""
        if self.platform.machine_type == 'wpc':
            return "FAST WPC"
        else:
            coil_index = 0
            number = Util.hex_string_to_int(self.number)
            for board_obj in self.platform.io_boards.values():
                if coil_index <= number < coil_index + board_obj.driver_count:
                    return "FAST Board {}".format(str(board_obj.node_id))
                coil_index += board_obj.driver_count

            # fall back if not found
            return "FAST Unknown Board"
