"""FAST Emulator Serial Communicator."""
# mpf/platforms/fast/communicators/emu.py

from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.00')  # override in subclass


class FastEmuCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the EMU processor on a FAST Retro Controller."""

    IGNORED_MESSAGES = []

    async def init(self):
        """Initialize the Emulation communicator. Not currently implemented."""

    async def soft_reset(self):
        """Soft reset the Emulation communicator. Not currently implemented."""