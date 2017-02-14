"""A kickback device which will fire a ball back into the playfield."""
from mpf.core.device_monitor import DeviceMonitor
from mpf.devices.autofire import AutofireCoil


@DeviceMonitor(_enabled="enabled")
class Kickback(AutofireCoil):

    """A kickback device which will fire a ball back into the playfield."""

    config_section = 'kickbacks'
    collection = 'kickbacks'
    class_label = 'kickback'

    def enable(self, **kwargs):
        """Add switch handler and call parent."""
        if not self._enabled:
            self.switch.add_handler(self._hit)

        super().enable(**kwargs)

    def disable(self, **kwargs):
        """Remove switch handler and call parent."""
        if self._enabled:
            self.switch.remove_handler(self._hit)

        super().enable(**kwargs)

    def _hit(self):
        """Post fired event."""
        self.machine.events.post("kickback_{}_fired".format(self.name))
        '''event: kickback_(name)_fired

        desc: Kickback fired a ball.
        '''
