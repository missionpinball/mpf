"""A Power Supply Unit (PSU) in a pinball machine."""
from mpf.core.system_wide_device import SystemWideDevice


class PowerSupplyUnit(SystemWideDevice):

    """Represents a power supply in a pinball machine."""

    config_section = 'psus'
    collection = 'psus'
    class_label = 'psu'

    __slots__ = ["_busy_until"]

    def __init__(self, machine, name):
        """Initialise PSU."""
        super().__init__(machine, name)
        self._busy_until = None

    def get_wait_time_for_pulse(self, pulse_ms, max_wait_ms) -> int:
        """Return a wait time for a pulse or 0."""
        current_time = self.machine.clock.get_time()

        if self._busy_until and self._busy_until < current_time:
            # prevent negative times
            self._busy_until = None

        if not self._busy_until or not max_wait_ms:
            # if we are not busy. do pulse now
            self.notify_about_instant_pulse(pulse_ms)
            return 0

        if self._busy_until > current_time + (max_wait_ms / 1000.0) or max_wait_ms is None:
            # if we are busy for longer than possible. do pulse now
            self.notify_about_instant_pulse(pulse_ms)
            return 0

        # calculate wait time and return it
        wait_ms = (self._busy_until - current_time) * 1000
        self._busy_until += (pulse_ms + self.config['release_wait_ms']) / 1000.0
        return wait_ms

    def notify_about_instant_pulse(self, pulse_ms):
        """Notify PSU about pulse."""
        if self._busy_until:
            self._busy_until = max(
                self._busy_until,
                self.machine.clock.get_time() + (pulse_ms + self.config['release_wait_ms']) / 1000.0)
        else:
            self._busy_until = self.machine.clock.get_time() + ((pulse_ms + self.config['release_wait_ms']) / 1000.0)
