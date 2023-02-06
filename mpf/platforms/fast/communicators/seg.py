from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.01')         # Minimum FW for a Segment Display

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

HEX_FORMAT = " 0x%02x"

class FastSegCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    ignored_messages = []

    async def init(self):

        # There are a bunch of seg displays out in the world with version FF.FF, so let's call those 0.9.
        if self.remote_firmware == 'FF.FF':
            self.remote_firmware = '0.01'

        if not self.platform._seg_task:
            self.machine.events.add_handler('machine_reset_phase_3', self.platform._start_seg_updates)

        await super().init()