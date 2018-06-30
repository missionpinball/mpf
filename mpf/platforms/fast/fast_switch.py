"""A switch conntected to a fast controller."""
import logging

from mpf.core.platform import SwitchConfig
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.fast.fast import FastHardwarePlatform


class FASTSwitch(SwitchPlatformInterface):

    """A switch conntected to a fast controller."""

    __slots__ = ["log", "connection", "send", "platform", "platform_settings", "_configured_debounce"]

    def __init__(self, config: SwitchConfig, number_tuple, platform: "FastHardwarePlatform", platform_settings) -> None:
        """Initialise switch."""
        super().__init__(config, number_tuple)
        self.log = logging.getLogger('FASTSwitch')
        self.connection = number_tuple[1]
        self.send = platform.net_connection.send
        self.platform = platform
        self.platform_settings = platform_settings
        self._configured_debounce = False
        self.configure_debounce(config.debounce in ("normal", "auto"))

    def get_board_name(self):
        """Return the board of this switch."""
        if self.platform.machine_type == 'wpc':
            return "FAST WPC"
        else:
            switch_index = 0
            number = Util.hex_string_to_int(self.number)
            for board_obj in self.platform.io_boards.values():
                if switch_index <= number < switch_index + board_obj.switch_count:
                    return "FAST Board {}".format(str(board_obj.node_id))
                switch_index += board_obj.switch_count

            # fall back if not found
            return "FAST Unknown Board"

    def configure_debounce(self, debounce):
        """Configure debounce settings."""
        if debounce:
            debounce_open = Util.int_to_hex_string(self.platform.config['default_normal_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.platform.config['default_normal_debounce_close'])
        else:
            debounce_open = Util.int_to_hex_string(self.platform.config['default_quick_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.platform.config['default_quick_debounce_close'])

        if 'debounce_open' in self.platform_settings and self.platform_settings['debounce_open'] is not None:
            debounce_open = self.platform.convert_number_from_config(self.platform_settings['debounce_open'])

        if 'debounce_close' in self.platform_settings and self.platform_settings['debounce_close'] is not None:
            debounce_close = self.platform.convert_number_from_config(self.platform_settings['debounce_close'])

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
