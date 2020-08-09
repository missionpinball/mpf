"""A kickback device which will fire a ball back into the playfield."""
from typing import List

from mpf.core.device_monitor import DeviceMonitor
from mpf.devices.autofire import AutofireCoil


@DeviceMonitor(_enabled="enabled")
class Kickback(AutofireCoil):

    """A kickback device which will fire a ball back into the playfield."""

    config_section = 'kickbacks'
    collection = 'kickbacks'
    class_label = 'kickback'

    __slots__ = []  # type: List[str]

    def _hit(self):
        """Post fired event."""
        super()._hit()
        if self._enabled:
            self.machine.events.post("kickback_{}_fired".format(self.name))
            '''event: kickback_(name)_fired

            desc: Kickback fired a ball.
            '''
