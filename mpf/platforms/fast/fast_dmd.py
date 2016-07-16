"""Fast DMD support."""


class FASTDMD(object):

    """Object for a FAST DMD."""

    def __init__(self, machine, sender):
        """Initialise DMD."""
        self.machine = machine
        self.send = sender

        # Clear the DMD
        # todo

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
            data: bytes to send to DMD
        """
        self.send(data)
