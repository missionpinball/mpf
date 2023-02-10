"""A switch conntected to a fast controller."""
import logging

from mpf.core.platform import SwitchConfig
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.fast.fast import FastHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import


class FASTSwitch(SwitchPlatformInterface):

    """A switch connected to a fast controller."""

    # __slots__ = ["log", "connection", "send", "platform_settings", "_configured_debounce"]

    def __init__(self, config: SwitchConfig, number_tuple, platform: "FastHardwarePlatform", platform_settings) -> None:
        """Initialise switch."""
        super().__init__(config, number_tuple, platform)
        self.log = logging.getLogger('FASTSwitch')
        self.is_network = number_tuple[1]
        self.connection = platform.serial_connections['net']
        self.platform_settings = platform_settings
        self._configured_debounce = False
        self.configure_debounce(config.debounce in ("normal", "auto"))

    def get_board_name(self):
        """Return the board of this switch."""
        if self.platform.is_retro:
            return f"FAST Retro ({self.platform.machine_type.upper()})"

        switch_index = 0
        number = Util.hex_string_to_int(self.number)
        for board_obj in self.platform.io_boards.values():
            if switch_index <= number < switch_index + board_obj.switch_count:
                return f"FAST Board {str(board_obj.node_id)}"
            switch_index += board_obj.switch_count

        # fall back if not found
        return "FAST Unknown Board"

    def configure_debounce(self, debounce):
        """Configure debounce settings."""

        # Set the debounce from the generic true/false first, then override if the platform settings have specific values
        if debounce:
            debounce_open = Util.int_to_hex_string(self.platform.config['net']['default_normal_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.platform.config['net']['default_normal_debounce_close'])
        else:
            debounce_open = Util.int_to_hex_string(self.platform.config['net']['default_quick_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.platform.config['net']['default_quick_debounce_close'])

        if 'debounce_open' in self.platform_settings and self.platform_settings['debounce_open'] is not None:
            debounce_open = self.platform.convert_number_from_config(self.platform_settings['debounce_open'])

        if 'debounce_close' in self.platform_settings and self.platform_settings['debounce_close'] is not None:
            debounce_close = self.platform.convert_number_from_config(self.platform_settings['debounce_close'])

        if self.is_network:  # TODO remove this if
            cmd = 'SN:'
        else:
            cmd = 'SL:'

        new_setting = (debounce_open, debounce_close)
        if new_setting == self._configured_debounce:
            return

        self._configured_debounce = new_setting

        final = '{}{},01,{},{}'.format(
            cmd,
            self.number[0],
            debounce_open,
            debounce_close)

        self.connection.send_and_confirm(final, f"{cmd}P")
