# mpf/platforms/fast/communicators/seg.py

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
        await self.send_and_wait_for_response_processed('ID:', 'ID:', max_retries=-1)  # Loop here until we get a response

    def start_tasks(self):

        for s in self.machine.device_manager.collections["segment_displays"]:
            self.platform.fast_segs.append(s.hw_display)

        self.platform.fast_segs.sort(key=lambda x: x.number)

        if self.platform.fast_segs:
            self.tasks.append(self.machine.clock.schedule_interval(self._update_segs,
                              1 / self.config['fps']))

    def _update_segs(self, **kwargs):
        for s in self.platform.fast_segs:

            if s.next_text:
                self.send_and_forget(f'PA:{s.hex_id},{s.next_text.convert_to_str()[0:7]}')
                s.next_text = None

            if s.next_color:
                self.send_and_forget(('PC:{},{}').format(s.hex_id, s.next_color))
                s.current_color = s.next_color
                s.next_color = None

    async def soft_reset(self):
        pass  # TODO turn off all segments

    def stopping(self):
        for s in self.platform.fast_segs:
            self.send_and_forget(f'PA:{s.hex_id},')
            s.next_text = None
            s.next_color = None
            s.current_color = None
