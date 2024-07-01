"""DMD Serial Communicator for FAST platforms."""
# mpf/platforms/fast/communicators/dmd.py

from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.88')  # override in subclass


class FastRgbDmdCommunicator(FastSerialCommunicator):

    """Handles the serial communication to a DMD in the FAST platform."""

    IGNORED_MESSAGES = []

    def send_frame(self, pixel_bytes):
        """Send a DMD frame to the platofrm."""
        # todo is this meth even used?
        self.send_bytes(b'BM:' + pixel_bytes, f'<{len(pixel_bytes)} bytes>')

    async def init(self):
        """Initialize the DMD display."""
        # Loop here until we get a response
        await self.send_and_wait_for_response_processed('ID:', 'ID:', max_retries=-1)

    async def soft_reset(self):
        """Send a soft reset (clear) to the DMD."""
        pixel_bytes = 128 * 32 * 3 * b'0'
        self.send_frame(pixel_bytes)
