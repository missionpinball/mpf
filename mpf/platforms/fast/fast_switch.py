"""A switch connected to a FAST controller."""
import logging

from mpf.core.utility_functions import Util

MYPY = False


class FASTSwitch:

    """A switch connected to a fast controller."""

    # __slots__ = ["log", "connection", "send", "platform_settings", "_configured_debounce"]

    def __init__(self, communicator, net_version, hw_number, ) -> None:
        """Initialise switch."""
        self.communicator = communicator
        self.net_version = net_version
        self.number = hw_number

        self.invert = False
        self.debounce = None
        self.platform = None
        self.active = False

        self.mode = 0
        self.debounce_open = 0
        self.debounce_close = 0

    def update_config(self, config, platform_settings):
        """Update config."""
        # TODO add validation

        self.configure_debounce(config, platform_settings)

        if self.invert:
            self.mode = 2
        else:
            self.mode = 1

    def send_config_to_switch(self):
        if self.net_version == 1:
            cmd = 'SN:'
        else:
            cmd = 'SL:'

        final = f'{cmd}{self.number},{self.mode},{self.debounce_open},{self.debounce_close}'

        self.communicator.send_and_confirm(final, f"{cmd}P")

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

    def configure_debounce(self, config, platform_settings):
        """Configure debounce settings."""

        # Set the debounce from the generic true/false first, then override if the platform settings have specific values
        if config.debounce in ['normal', 'auto']:
            debounce_open = Util.int_to_hex_string(self.communicator.config['default_normal_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.communicator.config['default_normal_debounce_close'])
        else:
            debounce_open = Util.int_to_hex_string(self.communicator.config['default_quick_debounce_open'])
            debounce_close = Util.int_to_hex_string(self.communicator.config['default_quick_debounce_close'])

        if 'debounce_open' in platform_settings and platform_settings['debounce_open'] is not None:
            debounce_open = self.communicator.platform.convert_number_from_config(platform_settings['debounce_open'])

        if 'debounce_close' in platform_settings and platform_settings['debounce_close'] is not None:
            debounce_close = self.communicator.platform.convert_number_from_config(platform_settings['debounce_close'])

        self.debounce_open = debounce_open
        self.debounce_close = debounce_close
