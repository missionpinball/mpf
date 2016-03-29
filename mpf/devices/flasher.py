""" Contains the Flasher parent class. """

from mpf.core.system_wide_device import SystemWideDevice


class Flasher(SystemWideDevice):
    """Generic class that holds flasher objects.
    """

    config_section = 'flashers'
    collection = 'flashers'
    class_label = 'flasher'

    def prepare_config(self, config, is_mode_config):
        del is_mode_config
        config['number_str'] = str(config['number']).upper()
        return config

    def _initialize(self):
        self.load_platform_section('flashers')

        self.hw_driver, self.number = self.platform.configure_driver(config=self.config)

        if self.config['flash_ms'] is None:
            self.config['flash_ms'] = self.machine.config['mpf']['default_flash_ms']

    def flash(self, milliseconds=None, **kwargs):
        """Flashes the flasher.

        Args:
            milliseconds: Int of how long you want the flash to be, in ms.
                Default is None which causes the flasher to flash for whatever
                its default config is, either its own flash_ms or the core-
                wide default_flash_ms settings. (Current default is 50ms.)

        """
        del kwargs

        if milliseconds is None:
            milliseconds = self.config['flash_ms']

        self.hw_driver.pulse(int(milliseconds))
