from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.88') # override in subclass

class FastDmdCommunicator(FastSerialCommunicator):

    """Handles the serial communication to a DMD in the FAST platform."""

    IGNORED_MESSAGES = []

    def _send(self, msg): # todo is this meth even used?
        self.send_bytes(b'BM:' + msg)

    async def soft_reset(self):
        pass  # TODO blank the screen
