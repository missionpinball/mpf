"""Contains the GI (General Illumination) parent classes."""
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("_brightness")
class Gi(SystemWideDevice):

    """Represents a light connected to a traditional lamp matrix in a pinball machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.
    """

    config_section = 'gis'
    collection = 'gis'
    class_label = 'gi'

    def __init__(self, machine, name):
        """Initialise GI."""
        self.hw_driver = None
        super().__init__(machine, name)

        self.registered_handlers = []
        self._brightness = 0

    def _initialize(self):
        self.load_platform_section('gis')

        self.hw_driver = self.platform.configure_gi(self.config)

    def enable(self, brightness=255, **kwargs):
        """Enable this GI string.

        Args:
            brightness: Int from 0-255 of how bright you want this to be. 255 is
                on. 0 os iff. Note that not all GI strings on all machines
                support this.
            fade_ms: How quickly you'd like this GI string to fade to this
                brightness level. This is not implemented.
        """
        del kwargs
        if isinstance(brightness, list):
            brightness = brightness[0]

        if self.registered_handlers:
            for handler in self.registered_handlers:
                handler(light_name=self.name, brightness=brightness)

        self.hw_driver.on(brightness)
        self._brightness = brightness

    def disable(self, **kwargs):
        """Disable this GI string."""
        del kwargs
        self._brightness = 0
        self.hw_driver.off()

    def add_handler(self, callback):
        """Register a handler to be called when this GI changes state."""
        self.registered_handlers.append(callback)

    def remove_handler(self, callback=None):
        """Remove a handler from the list of registered handlers."""
        if not callback:  # remove all
            self.registered_handlers = []
            return

        if callback in self.registered_handlers:
            self.registered_handlers.remove(callback)
