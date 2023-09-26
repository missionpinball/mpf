from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.01')         # Minimum FW for a Segment Display

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

class FastSegCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    IGNORED_MESSAGES = []

    async def init(self):
        await super().init()

        self._seg_task = None

    def start_tasks(self):
        """Start the communicator."""

        for s in self.machine.device_manager.collections["segment_displays"]:
            self.platform.fast_segs.append(s.hw_display)

        self.platform.fast_segs.sort(key=lambda x: x.number)

        if self.platform.fast_segs:
            self._seg_task = self.machine.clock.schedule_interval(self._update_segs,
                                                1 / self.config['fps'])

    def _update_segs(self, **kwargs):
        for s in self.platform.fast_segs:

            if s.next_text:
                self.send_and_forget(f'PA:{s.hex_id},{s.next_text.convert_to_str()[0:7]}')
                s.next_text = None

            if s.next_color:
                self.send_and_forget(('PC:{},{}').format(s.hex_id, s.next_color))
                s.next_color = None

    def _process_id(self, msg):
        """Process the ID response."""

        # No FW comparison as some have v 'FF.FF' We can fix this for real in the future if the
        # firmware is changed in a way that matters for MPF.

        # TODO make this actually check each display
        self.remote_processor, self.remote_model, self.remote_firmware = msg.split()
        self.platform.log.info(f"Connected to SEG processor on {self.remote_model} with firmware v{self.remote_firmware}")

    async def soft_reset(self):
        pass  # TODO turn off all segments

    def stopping(self):
        if self._seg_task:
            self._seg_task.cancel()
            self._seg_task = None

        # TODO Better way to do this?
        for s in self.platform.fast_segs:
            self.send_and_forget(f'PA:{s.hex_id},        ')
            s.next_text = None
            s.next_color = None
