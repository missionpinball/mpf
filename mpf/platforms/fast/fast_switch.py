"""A switch conntected to a fast controller."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface


class FASTSwitch(SwitchPlatformInterface):

    """A switch conntected to a fast controller."""

    def __init__(self, config, sender, platform):
        """Initialise switch."""
        super().__init__(config, config['number'])
        self.log = logging.getLogger('FASTSwitch')
        self.connection = config['number'][1]
        self.send = sender
        self.platform = platform
        self._configured_debounce = False
        self.configure_debounce(config)

    def configure_debounce(self, config):
        """Configure debounce settings."""
        if config['debounce'] in ("normal", "auto"):
            debounce_open = Util.int_to_hex_string(self.platform.config['default_normal_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.platform.config['default_normal_debounce_close'])
        else:
            debounce_open = Util.int_to_hex_string(self.platform.config['default_quick_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.platform.config['default_quick_debounce_close'])

        if 'debounce_open' in config and config['debounce_open'] is not None:
            debounce_open = self.platform.convert_number_from_config(config['debounce_open'])

        if 'debounce_close' in config and config['debounce_close'] is not None:
            debounce_close = self.platform.convert_number_from_config(config['debounce_close'])

        if self.connection:
            cmd = 'SN:'
        else:
            cmd = 'SL:'

        new_setting = (debounce_open, debounce_close)
        if new_setting == self._configured_debounce:
            return

        self._configured_debounce = new_setting

        cmd = '{}{},01,{},{}'.format(
            cmd,
            self.number[0],
            debounce_open,
            debounce_close)

        self.send(cmd)
