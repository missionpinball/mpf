"""PKONE EX2 board."""
import logging


# pylint: disable-msg=too-few-public-methods
class PKONEEX2Board:

    """PKONE EX2 board with switches, optos, coils and servos."""

    __slots__ = ["log", "addr", "firmware_version", "hardware_rev", "switch_count",
                 "coil_count", "servo_count"]

    def __init__(self, addr, firmware_version, hardware_rev):
        """Initialize a PKONE EX2 board."""
        self.log = logging.getLogger('PKONEEX2Board {}'.format(addr))
        self.addr = addr
        self.firmware_version = firmware_version
        self.hardware_rev = hardware_rev
        self.switch_count = 35  # inputs 1-30 are switches; 31-35 are optos
        self.coil_count = 10  # outputs 1-10
        self.servo_count = 4  # outputs 11-14

    def get_description_string(self) -> str:
        """Return description string."""
        return "PKONE EX2 Board {} - Firmware: {}, Hardware Rev: {}, " \
               "Switches/Optos: {}, Coils: {}, Servos: {}".format(
                   self.addr,
                   self.firmware_version,
                   self.hardware_rev,
                   self.switch_count,
                   self.coil_count,
                   self.servo_count)
