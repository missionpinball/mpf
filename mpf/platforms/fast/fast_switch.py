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
            debounce_open = self.platform.config['default_normal_debounce_open']
            debounce_close = self.platform.config['default_normal_debounce_close']
        else:
            debounce_open = self.platform.config['default_quick_debounce_open']
            debounce_close = self.platform.config['default_quick_debounce_close']

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
            Util.int_to_hex_string(debounce_open),
            Util.int_to_hex_string(debounce_close))

        self.send(cmd)
