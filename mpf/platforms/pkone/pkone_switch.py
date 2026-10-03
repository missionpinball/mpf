"""A switch input on a PKONE EX2 or Switch board."""
import logging
from collections import namedtuple
from typing import TYPE_CHECKING

from mpf.core.platform import SwitchConfig
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface


if TYPE_CHECKING:
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import

PKONESwitchNumber = namedtuple("PKONESwitchNumber", ["board_address_id", "switch_number"])


# pylint: disable-msg=too-few-public-methods
class PKONESwitch(SwitchPlatformInterface):

    """A PKONE input on an EX2 or Switch board."""

    __slots__ = ["log"]

    def __init__(self, config: SwitchConfig, number: PKONESwitchNumber, platform: "PKONEHardwarePlatform") -> None:
        """Initialize switch."""
        super().__init__(config, number, platform)
        self.log = logging.getLogger('PKONESwitch')

    def get_board_name(self):
        """Return the owning PKONE board name."""
        address = self.number.board_address_id
        if address in self.platform.pkone_ex2_boards:
            return "PKONE EX2 Board {}".format(address)
        if address in self.platform.pkone_switch_boards:
            return "PKONE Switch Board {}".format(address)
        return "PKONE Unknown Board"

class PKONESwitchBoard:
    """PKONE Switch board with 40 inputs and no enabled outputs."""
    __slots__ = ["log", "addr", "firmware_version", "hardware_rev", "switch_count",
                 "coil_count", "servo_count"]

    def __init__(self, addr, firmware_version, hardware_rev):
        self.log = logging.getLogger('PKONESwitchBoard {}'.format(addr))
        self.addr = addr
        self.firmware_version = firmware_version
        self.hardware_rev = hardware_rev
        self.switch_count = 40
        self.coil_count = 0
        self.servo_count = 0

    def get_description_string(self):
        return (f"PKONE Switch Board {self.addr} - Firmware: {self.firmware_version}, "
                f"Hardware Rev: {self.hardware_rev}, Switches: 40, Coil outputs disabled")
