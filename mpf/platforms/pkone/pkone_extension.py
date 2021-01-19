"""PKONE Extension board."""
import logging


class PKONEExtensionBoard:
    """PKONE Extension board."""

    __slots__ = ["log", "addr"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, addr):
        """Initialize PKONE Extension board."""
        self.log = logging.getLogger('PKONEExtensionBoard {}'.format(addr))
        self.addr = addr
