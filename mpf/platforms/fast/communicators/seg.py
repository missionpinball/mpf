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

        if not self.platform._seg_task:
            self.machine.events.add_handler('machine_reset_phase_3', self.platform._start_seg_updates)
            # TODO formalize and move

        await super().init()

    def _process_id(self, msg):
        """Process the ID response."""

        # No FW comparison as some have v 'FF.FF' We can fix this for real in the future if the
        # firmware is changed in a way that matters for MPF.

        self.remote_processor, self.remote_model, self.remote_firmware = msg.split()

        self.platform.log.info(f"Connected to {self.remote_processor} processor on {self.remote_model} with firmware v{self.remote_firmware}")

        self.machine.variables.set_machine_var("fast_{}_firmware".format(self.remote_processor.lower()),
                                               self.remote_firmware)

        self.machine.variables.set_machine_var("fast_{}_model".format(self.remote_processor.lower()), self.remote_model)
