from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

HEX_FORMAT = " 0x%02x"

MIN_FW = version.parse('0.88') # override in subclass

class FastDmdCommunicator(FastSerialCommunicator):

    """Handles the serial communication to a DMD in the FAST platform."""

    ignored_messages = []

    def _send(self, msg):
        self.writer.write(b'BM:' + msg)

        if self.platform.config['debug']:
            self.platform.log.debug(f"Send: BM: {len(msg)} bytes")
