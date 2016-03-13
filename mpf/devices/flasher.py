""" Contains the Flasher parent class. """

from mpf.core.device import Device


class Flasher(Device):
    """Generic class that holds flasher objects.
    """

    config_section = 'flashers'
    collection = 'flashers'
    class_label = 'flasher'

    def __init__(self, machine, name, config=None, validate=True):
        # TODO: why?
        config['number_str'] = str(config['number']).upper()

        super().__init__(machine, name, config, platform_section='flashers', validate=validate)


    def _initialize(self):
        self.hw_driver, self.number = (
            self.platform.configure_driver(config=self.config,
                                           device_type='flasher'))

        if self.config['flash_ms'] is None:
            self.config['flash_ms'] = (
                self.machine.config['mpf']['default_flash_ms'])

    def flash(self, milliseconds=None):
        """Flashes the flasher.

        Args:
            milliseconds: Int of how long you want the flash to be, in ms.
                Default is None which causes the flasher to flash for whatever
                its default config is, either its own flash_ms or the core-
                wide default_flash_ms settings. (Current default is 50ms.)

        """

        if milliseconds is None:
            milliseconds = self.config['flash_ms']

        self.hw_driver.pulse(int(milliseconds))
