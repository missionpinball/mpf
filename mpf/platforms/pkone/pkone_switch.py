"""A switch input on a PKONE Extension board."""
import logging
from collections import namedtuple
from typing import TYPE_CHECKING

from mpf.core.platform import SwitchConfig
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.pkone.pkone_extension import PKONEExtensionBoard


if TYPE_CHECKING:
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import

PKONESwitchNumber = namedtuple("PKONESwitchNumber", ["board_address_id", "switch_number"])


# pylint: disable-msg=too-few-public-methods
class PKONESwitch(SwitchPlatformInterface):

    """An PKONE input on a PKONE Extension board."""

    __slots__ = ["log"]

    def __init__(self, config: SwitchConfig, number: PKONESwitchNumber, platform: "PKONEHardwarePlatform") -> None:
        """Initialize switch."""
        super().__init__(config, number, platform)
        self.log = logging.getLogger('PKONESwitch')

    def get_board_name(self):
        """Return PKONE Extension addr."""
        if self.number.board_address_id not in self.platform.pkone_extensions.keys():
            return "PKONE Unknown Board"
        return "PKONE Extension Board {}".format(self.number.board_address_id)

class PKONESwitchBoard(PKONEExtensionBoard):
    """Use the existing input interface without claiming Extension outputs."""
    __slots__ = []

    def __init__(self, addr, firmware_version, hardware_rev):
        super().__init__(addr, firmware_version, hardware_rev)
        self.switch_count = 40
        self.coil_count = 0
        self.servo_count = 0

    def get_description_string(self):
        return (f"PKONE Switch Board {self.addr} - Firmware: {self.firmware_version}, "
                f"Hardware Rev: {self.hardware_rev}, Switches: 40, Outputs disabled (development)")
