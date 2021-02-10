"""PKONE Extension board."""
import logging


class PKONEExtensionBoard:
    """PKONE Extension board."""

    __slots__ = ["log", "addr", "firmware_version", "hardware_rev", "switch_count", "opto_count",
                 "driver_count", "servo_count"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, addr, firmware_version, hardware_rev):
        """Initialize PKONE Extension board."""
        self.log = logging.getLogger('PKONEExtensionBoard {}'.format(addr))
        self.addr = addr
        self.firmware_version = firmware_version
        self.hardware_rev = hardware_rev
        self.switch_count = 30  # numbers 1 - 30
        self.opto_count = 5     # numbers 1 - 5
        self.driver_count = 10  # numbers 1 - 10
        self.servo_count = 4    # numbers 11-14

    def get_description_string(self) -> str:
        """Return description string."""
        return "PKONE Extension Board {} - Firmware: {}, Hardware Rev: {}, " \
               "Switches: {}, Optos: {}, Drivers: {}, Servos: {}".format(
            self.addr,
            self.firmware_version,
            self.hardware_rev,
            self.switch_count,
            self.opto_count,
            self.driver_count,
            self.servo_count
        )
