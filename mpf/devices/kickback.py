"""A kickback device which will fire a ball back into the playfield."""
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.devices.autofire import AutofireCoil


@DeviceMonitor(_enabled="enabled")
class Kickback(AutofireCoil):

    """A kickback device which will fire a ball back into the playfield."""

    config_section = 'kickbacks'
    collection = 'kickbacks'
    class_label = 'kickback'

    def _hit(self):
        """Post fired event."""
        super()._hit()
        if self._enabled:
            self.machine.events.post("kickback_{}_fired".format(self.name))
            '''event: kickback_(name)_fired

            desc: Kickback fired a ball.
            '''
