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

    @event_handler(10)
    def enable(self, **kwargs):
        """Add switch handler and call parent."""
        if not self._enabled:
            self.config['switch'].add_handler(self._hit)

        super().enable(**kwargs)

    @event_handler(1)
    def disable(self, **kwargs):
        """Remove switch handler and call parent."""
        if self._enabled:
            self.config['switch'].remove_handler(self._hit)

        super().disable(**kwargs)

    def _hit(self):
        """Post fired event."""
        self.machine.events.post("kickback_{}_fired".format(self.name))
        '''event: kickback_(name)_fired

        desc: Kickback fired a ball.
        '''
