"""Fast DMD support."""
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface


class FASTDMD(DmdPlatformInterface):

    """Object for a FAST DMD."""

    def __init__(self, machine, sender):
        """Initialise DMD."""
        self.machine = machine
        self.send = sender

        # Clear the DMD
        # todo

    def set_brightness(self, brightness: float):
        """Set brightness."""
        # not supported
        assert brightness == 1.0

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
            data: bytes to send to DMD
        """
        self.send(data)
