"""PKONE Extension board."""
import logging


# pylint: disable-msg=too-few-public-methods
class PKONEExtensionBoard:

    """PKONE Extension board."""

    __slots__ = ["log", "addr", "firmware_version", "hardware_rev", "switch_count",
                 "coil_count", "servo_count"]

    def __init__(self, addr, firmware_version, hardware_rev):
        """Initialize PKONE Extension board."""
        self.log = logging.getLogger('PKONEExtensionBoard {}'.format(addr))
        self.addr = addr
        self.firmware_version = firmware_version
        self.hardware_rev = hardware_rev
        self.switch_count = 35  # numbers 1 - 35 (31-35 are NC opto switches)
        self.coil_count = 10  # numbers 1 - 10
        self.servo_count = 4    # numbers 11-14

    def get_description_string(self) -> str:
        """Return description string."""
        return "PKONE Extension Board {} - Firmware: {}, Hardware Rev: {}, " \
               "Switches: {}, Coils: {}, Servos: {}".format(
                   self.addr,
                   self.firmware_version,
                   self.hardware_rev,
                   self.switch_count,
                   self.coil_count,
                   self.servo_count)
