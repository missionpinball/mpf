from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.00') # override in subclass

class FastEmuCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the EMU processor on a FAST Retro Controller."""

    IGNORED_MESSAGES = []
