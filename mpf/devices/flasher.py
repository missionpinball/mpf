"""Contains the Flasher parent class."""

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.driver import ConfiguredHwDriver


class Flasher(SystemWideDevice):

    """Generic class that holds flasher objects."""

    config_section = 'flashers'
    collection = 'flashers'
    class_label = 'flasher'

    def __init__(self, machine, name):
        """Initialise flasher."""
        self._configured_driver = None
        self.hw_driver = None
        super().__init__(machine, name)

    def _initialize(self):
        self.load_platform_section('flashers')

        self.hw_driver = self.platform.configure_driver(config=self.config)

        if self.config['flash_ms'] is None:
            self.config['flash_ms'] = self.machine.config['mpf']['default_flash_ms']

    def get_configured_driver(self):
        """Reconfigure driver."""
        if not self._configured_driver:
            self._configured_driver = ConfiguredHwDriver(self.hw_driver, {})
        return self._configured_driver

    def flash(self, milliseconds=None, **kwargs):
        """Flashe the flasher.

        Args:
            milliseconds: Int of how long you want the flash to be, in ms.
                Default is None which causes the flasher to flash for whatever
                its default config is, either its own flash_ms or the core-
                wide default_flash_ms settings. (Current default is 50ms.)
        """
        del kwargs

        if milliseconds is None:
            milliseconds = self.config['flash_ms']

        self.hw_driver.pulse(self.get_configured_driver(), int(milliseconds))
