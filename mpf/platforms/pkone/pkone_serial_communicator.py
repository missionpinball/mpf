"""PKONE serial communicator."""
import asyncio

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform   # pylint: disable-msg=cyclic-import,unused-import

# Minimum firmware versions needed for this module
MIN_FW = 0x00000100
BAD_FW_VERSION = 0x01020304


class PKONESerialCommunicator(BaseSerialCommunicator):

    """Handles the serial communication to the PKONE platform."""

    __slots__ = ["part_msg", "chain_serial", "_lost_synch"]

    # pylint: disable=too-many-arguments
    def __init__(self, platform: "PKONEHardwarePlatform", port, baud) -> None:
        """Initialise Serial Connection to PKONE Hardware."""

        super().__init__(platform, port, baud)
